# Minecraft Proxy module specification

## Template and runtime

| Setting | Value |
| --- | --- |
| Module, template and game ID | `minecraft-proxy` |
| Module and template version | `1.0.0` |
| Minimum Gameplane version | `0.4.1` |
| Image | `itzg/mc-proxy:2026.11.1-java25@sha256:8efdaa9d990f4c509f21b7ced003dd959060777784422fd72fdd537d613c1813` |
| Linux architectures | `amd64`, `arm64` |
| User, group and filesystem group | `1000` |
| Working directory and `HOME` | `/server` |
| Primary volume | `1Gi` at `/server` |
| CPU request and limit | `100m` and `1` |
| Memory request and limit | `256Mi` and `1Gi` |

| `spec.version` | Image `TYPE` | Loader | Active routing file |
| --- | --- | --- | --- |
| `velocity` (default) | `VELOCITY` | `velocity` | `/server/velocity.toml` |
| `waterfall` | `WATERFALL` | `waterfall` | `/server/config.yml` |
| `bungeecord` | `BUNGEECORD` | `bungeecord` | `/server/config.yml` |

The fallback image environment selects `VELOCITY`. Each loader mounts its own
plugin PVC at `/server/plugins` and accepts `.jar` uploads and allowlisted
URL installs. Switching types retains the other PVCs. The primary GameServer
backup covers the data PVC. Back up each plugin PVC separately.

## Startup, routing and persistence

The operator renders `gameplane-defaults/config.yml` and
`gameplane-defaults/velocity.toml` on the data PVC every pod start. Both use
`INITIAL_BACKEND` (default `lobby:25565`) for the seed route named `lobby`.
The wrapper copies the active seed when its routing file is absent, then
hands off to `/usr/bin/run-bungeecord.sh`. It sets `umask 0007` to allow
shared group access and restrict permissions for other users.

The two live routing files persist independently. Waterfall and BungeeCord
read the same `config.yml`. Existing live files take precedence over seeds,
including after a change to `INITIAL_BACKEND`. Edit the live routing file to
add backend servers, fallback priorities, or forced hosts.

Both seeds bind TCP `0.0.0.0:25565`, authenticate clients, route to `lobby`,
and disable query. The Bungee-family seed enables legacy IP forwarding with
`ip_forward: true`. The Velocity 2.7 seed enables modern forwarding with
`forwarding.secret`. The upstream launcher creates the secret if it is absent
and reuses it on later starts. Restrict direct access to the offline-mode
backends and configure them for the matching forwarding format.

Waterfall runs archived `1.21` build `615`. Its bundled module downloader
uses the legacy PaperMC API. The wrapper fetches six matching JARs from
PaperMC's content-addressed store and checks them against the operator-rendered
`gameplane-defaults/waterfall-modules.sha256` before starting the proxy.
For Waterfall and BungeeCord, the wrapper creates `modules` and `modules.yml`
links at the data root when absent. These resolve under
`plugins/.gameplane-proxy-modules` in the active type's plugin PVC.
[Waterfall module downloader source](https://github.com/PaperMC/Waterfall/blob/150a002/BungeeCord-Patches/0006-Fetch-modules-from-the-Waterfall-API-endpoint.patch), [PaperMC build metadata](https://fill.papermc.io/v3/projects/waterfall/versions/1.21/builds/615)

## Probes, console and JVM

- The public port is `game` on TCP 25565. Startup, readiness and liveness use
  `/usr/bin/health.sh` with `SERVER_PORT=25565`. The startup probe budgets
  60 attempts at 10-second intervals for installation and startup.
- The internal `rcon` port is TCP 25575 and uses the Source RCON protocol.
  Gameplane injects `RCON_PASSWORD` from its generated Secret and the
  upstream launcher enables the appropriate RCON plugin. Lifecycle stop
  sends the `end` command.
- `INIT_MEMORY` defaults to `128M`. `MAX_MEMORY` defaults to 75% of the
  effective memory limit, computed by Gameplane as a Java heap size in
  mebibytes. `JVM_OPTS` and `JVM_XX_OPTS` pass optional JVM arguments. All
  four settings apply at restart.

See the [setup guide](README.md) for credential rotation and backend
configuration. The image's [pinned launcher source](https://github.com/itzg/docker-mc-proxy/blob/89a7d3ad7dc6f9e8a93d52224c3899e06f8a89ac/scripts/run-bungeecord.sh)
defines upstream downloads and initialization behavior.
