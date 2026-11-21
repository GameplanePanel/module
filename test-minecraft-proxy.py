"""Exercise the proxy module's real configs, image, probes, RCON, and restart.

Requires Python 3.11+, PyYAML, Go, Docker, and upstream download access.
No host ports are published. Only uniquely named test containers/volumes are removed.
"""

from pathlib import Path, PurePosixPath
import json
import os
import secrets
import subprocess
import tempfile
import time
import tomllib
import unittest
import uuid

import yaml


ROOT = Path(__file__).resolve().parent


def run(*args, check=True, **kwargs):
    return subprocess.run(args, check=check, capture_output=True, text=True,
                          encoding="utf-8", timeout=180, **kwargs)


class MinecraftProxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "minecraft-proxy/template.yaml"
        if not path.exists():
            raise AssertionError("Minecraft Proxy module is missing")
        cls.spec = yaml.safe_load(path.read_text(encoding="utf-8"))["spec"]
        # A GameServer keeps the same generated secret when switching loaders.
        cls.rcon_password = secrets.token_urlsafe(24)
        cls.temp = tempfile.TemporaryDirectory(prefix="gameplane-proxy-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.renderer = str(Path(cls.temp.name) / ("render.exe" if os.name == "nt" else "render"))
        run("go", "build", "-o", cls.renderer, str(ROOT / "testdata/render-config.go"))

    def render(self, **overrides):
        values = {f["name"]: f.get("default", "") for f in self.spec["configSchema"]}
        values.update(overrides)
        result = run(self.renderer, input=json.dumps({
            "Files": self.spec["configFiles"], "Values": values,
            "Server": {"Name": "proxy-test", "Namespace": "games"},
        }))
        return json.loads(result.stdout)

    def test_seed_configs_route_to_initial_backend(self):
        # Wrong quoting, field binding, listener port or default host routing
        # would prevent an operator-generated config from working.
        files = self.render(INITIAL_BACKEND="lobby.games.svc.cluster.local:25565")
        bungee = yaml.safe_load(files["gameplane-defaults/config.yml"])
        velocity = tomllib.loads(files["gameplane-defaults/velocity.toml"])
        self.assertEqual(bungee["servers"]["lobby"]["address"], "lobby.games.svc.cluster.local:25565")
        self.assertEqual(velocity["servers"]["lobby"], "lobby.games.svc.cluster.local:25565")
        self.assertEqual(bungee["listeners"][0]["host"], "0.0.0.0:25565")
        self.assertEqual(velocity["bind"], "0.0.0.0:25565")
        self.assertEqual(bungee["listeners"][0]["forced_hosts"], {})
        self.assertEqual(velocity["forced-hosts"], {})
        self.assertTrue(bungee["online_mode"])
        self.assertTrue(velocity["online-mode"])
        self.assertEqual(velocity["player-info-forwarding-mode"], "modern")
        # Input must remain a scalar, never become executable config syntax.
        odd = 'backend"\\name:25565\n[next]'
        files = self.render(INITIAL_BACKEND=odd)
        self.assertEqual(yaml.safe_load(files["gameplane-defaults/config.yml"])["servers"]["lobby"]["address"], odd)
        self.assertEqual(tomllib.loads(files["gameplane-defaults/velocity.toml"])["servers"]["lobby"], odd)

    def wait_ready(self, name):
        command = self.spec["probes"]["readiness"]["exec"]["command"]
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            state = run("docker", "inspect", "--format", "{{.State.Running}}", name).stdout.strip()
            if state != "true":
                logs = run("docker", "logs", name)
                self.fail("Proxy exited during startup:\n" + logs.stdout + logs.stderr)
            if run("docker", "exec", name, *command, check=False).returncode == 0:
                # The game listener may open just before the RCON plugin.
                response = run("docker", "exec", name, "rcon-cli", "help", check=False)
                if response.returncode == 0 and response.stdout.strip():
                    return
            time.sleep(2)
        logs = run("docker", "logs", name)
        self.fail("Proxy did not become ready:\n" + logs.stdout + logs.stderr)

    def stop_gracefully(self, name):
        for command in self.spec["capabilities"]["lifecycle"]["stop"]:
            # A successful shutdown can close RCON before it sends a reply.
            run("docker", "exec", name, "rcon-cli", command, check=False)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = json.loads(run("docker", "inspect", "--format", "{{json .State}}", name).stdout)
            if not state["Running"]:
                self.assertEqual(state["ExitCode"], 0)
                return
            time.sleep(1)
        self.fail("Declared lifecycle command did not stop the proxy")

    def exercise_proxy(self, version, retained_volumes=None):
        image = version["image"]
        data_path = PurePosixPath(self.spec["storage"]["mountPath"])
        loader = self.spec["capabilities"]["mods"]["loaders"][version["loader"]]
        plugin_path = data_path / loader["path"]
        security = self.spec["security"]
        user = f"{security['runAsUser']}:{security['runAsGroup']}"
        token = "gp-proxy-test-" + uuid.uuid4().hex[:12]
        data, plugins = retained_volumes or (token + "-data", token + "-plugins")
        containers, volumes = [], []
        try:
            if retained_volumes is None:
                for volume in (data, plugins):
                    run("docker", "volume", "create", volume)
                    volumes.append(volume)
            mounts = ["-v", f"{data}:{data_path}", "-v", f"{plugins}:{plugin_path}"]
            # Give disposable volumes writable ownership for the declared game user.
            run("docker", "run", "--rm", "--user", "0:0", *mounts,
                "--entrypoint", "/bin/bash", image, "-ec",
                'mkdir -p "$1/gameplane-defaults"; chown -R -- "$2" "$1"',
                "test", str(data_path), user)
            env = {e["name"]: e["value"] for e in self.spec.get("env", [])}
            env.update({e["name"]: e["value"] for e in version.get("env", [])})
            for field in self.spec["configSchema"]:
                if field.get("target", "env") == "env" and field.get("default"):
                    env[field.get("envName", field["name"])] = field["default"]
            env.update(MAX_MEMORY="512M", RCON_PASSWORD=self.rcon_password)
            args = ["docker", "create", "--name", token, "--memory", "1g",
                    "--user", user, *mounts]
            for key, value in env.items():
                args.extend(["-e", key + "=" + value])
            command = self.spec["command"] + self.spec.get("args", [])
            args.extend(["--entrypoint", command[0], image, *command[1:]])
            run(*args)
            containers.append(token)
            files = self.render(INITIAL_BACKEND="127.0.0.1:25566")
            with tempfile.TemporaryDirectory(prefix="proxy-config-") as directory:
                for index, (path, content) in enumerate(files.items()):
                    source = Path(directory) / str(index)
                    source.write_bytes(content.encode("utf-8"))
                    run("docker", "cp", str(source), f"{token}:{data_path / path}")
            run("docker", "start", token)
            self.wait_ready(token)
            # A healthy listener can still be missing bundled proxy commands
            # when Waterfall's retired module download API fails.
            online = run("docker", "exec", token, "rcon-cli", "glist").stdout
            self.assertRegex(online, r"\b0\b", "Proxy player-list command is unavailable: " + online)
            transfer = run("docker", "exec", token, "rcon-cli", "send").stdout
            self.assertRegex(transfer.lower(), r"send\s+<", "Proxy transfer command is unavailable: " + transfer)
            # Both advertised game port and local-only RCON are now exercised.
            config = "velocity.toml" if version["id"] == "velocity" else "config.yml"
            run("docker", "exec", token, "bash", "-ec",
                'sed -i s/127.0.0.1:25566/127.0.0.1:25567/g "$1"; '
                'printf "preserved plugin data" > /server/plugins/persistence-proof.txt', "test", "/server/" + config)
            parse = tomllib.loads if version["id"] == "velocity" else yaml.safe_load
            original = parse(run("docker", "exec", token, "cat", "/server/" + config).stdout)
            address = original["servers"]["lobby"]
            self.assertEqual(address if isinstance(address, str) else address["address"], "127.0.0.1:25567")
            secret = None
            if version["id"] == "velocity":
                secret = run("docker", "exec", token, "cat", "/server/forwarding.secret").stdout
                self.assertTrue(secret.strip(), "Velocity did not generate a forwarding secret")
            self.stop_gracefully(token)
            run("docker", "start", token)
            self.wait_ready(token)
            # Bungee-family proxies reserialize YAML, including key ordering
            # and comments. Routing values, rather than formatting, must survive.
            self.assertEqual(parse(run("docker", "exec", token, "cat", "/server/" + config).stdout), original)
            self.assertEqual(run("docker", "exec", token, "cat", str(plugin_path / "persistence-proof.txt")).stdout,
                             "preserved plugin data")
            if secret is not None:
                self.assertEqual(run("docker", "exec", token, "cat", "/server/forwarding.secret").stdout, secret)
            self.stop_gracefully(token)
        except BaseException:
            for container in containers:
                logs = run("docker", "logs", container, check=False)
                print(logs.stdout, logs.stderr)
            raise
        finally:
            for container in containers:
                run("docker", "rm", "-f", container, check=False)
            for volume in volumes:
                run("docker", "volume", "rm", volume, check=False)

    def test_velocity_boot_console_stop_and_preserve_edits(self):
        self.exercise_proxy(next(v for v in self.spec["versions"] if v["id"] == "velocity"))

    def test_waterfall_boot_console_stop_and_preserve_edits(self):
        self.exercise_proxy(next(v for v in self.spec["versions"] if v["id"] == "waterfall"))

    def test_bungeecord_boot_console_stop_and_preserve_edits(self):
        self.exercise_proxy(next(v for v in self.spec["versions"] if v["id"] == "bungeecord"))

    def test_switching_bungee_family_keeps_core_modules_compatible(self):
        # The operator retains the data PVC but swaps the plugin PVC by loader.
        # BungeeCord bootstrap modules and Waterfall Jenkins modules must not
        # inherit each other's modules.yml or command jars after a type switch.
        token = "gp-proxy-test-" + uuid.uuid4().hex[:12]
        data = token + "-data"
        versions = {v["id"]: v for v in self.spec["versions"]}
        sequence = [versions[name] for name in ("bungeecord", "waterfall", "bungeecord")]
        plugins = {version["id"]: token + "-" + version["id"] for version in sequence}
        volumes = []
        try:
            for volume in (data, *plugins.values()):
                run("docker", "volume", "create", volume)
                volumes.append(volume)
            for version in sequence:
                with self.subTest(proxy=version["id"]):
                    self.exercise_proxy(version, (data, plugins[version["id"]]))
        finally:
            for volume in volumes:
                run("docker", "volume", "rm", volume, check=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
