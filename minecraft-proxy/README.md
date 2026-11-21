# Minecraft Proxy

Route Minecraft Java Edition players to one or more backend servers. The
module requires Gameplane 0.4.1 or later.

## Create the proxy

1. Select **Minecraft Proxy** in the New Server wizard. Choose **Velocity**
   (the default), **Waterfall**, or **BungeeCord**. PaperMC has ended support
   for Waterfall. [Waterfall end-of-life notice](https://papermc.io/software/waterfall/)
2. In **Initial lobby address**, enter a `host:port` reachable from the proxy
   pod. The default `lobby:25565` fits a GameServer named `lobby` in the same
   namespace. Use the backend's internal Service DNS name across namespaces.
3. Expose the proxy's `game` port (TCP 25565) to players. Keep TCP 25575
   private for RCON and restrict the backend game ports to the proxy.

For a local install, run this command from the modules repository root with
the Gameplane CRDs installed and the operator at version 0.4.1 or later.

```sh
kubectl apply -f minecraft-proxy/template.yaml
```

For Kubernetes manifests, start with the [Velocity sample](samples/velocity.yaml),
[Waterfall sample](samples/waterfall.yaml), or [BungeeCord sample](samples/bungeecord.yaml).
Set the namespace and lobby address for your cluster.

## Configure backend forwarding

Keep the proxy in online mode so it authenticates players. Give backends
private addresses and enforce access to their game ports at the network layer.
Gameplane's default ingress policy allows `0.0.0.0/0` to advertised backend
game ports, including on ClusterIP services. Kubernetes combines the allow
rules from all applicable NetworkPolicies. If you use NetworkPolicy for
isolation, change Gameplane's ingress configuration to narrow or remove its
broad rule and check the other effective rules. You can also restrict access
with network or firewall rules that enforce the proxy-only path.
[Kubernetes NetworkPolicy rules](https://kubernetes.io/docs/concepts/services-networking/network-policies/#the-two-sorts-of-pod-isolation), [PaperMC backend security guide](https://docs.papermc.io/velocity/security/)

Verify that the proxy can connect and that direct connections from clients
and other untrusted workloads fail. Then set `online-mode=false` in the
backend's `server.properties`. For a Gameplane Minecraft Java backend, set
**Online mode** to `false`.

- **Velocity** uses modern forwarding. On a current Paper backend, disable
  `settings.bungeecord` in `spigot.yml`. In `config/paper-global.yml`, enable
  `proxies.velocity.enabled`, set `proxies.velocity.online-mode` to `true`,
  and set `proxies.velocity.secret` to the contents of the proxy's
  `forwarding.secret`. The image creates that file on Velocity's first
  launch and keeps it on the data volume. Use a backend that supports modern
  forwarding. [Velocity forwarding guide](https://docs.papermc.io/velocity/player-information-forwarding/#configuring-modern-forwarding)
- **Waterfall and BungeeCord** use `ip_forward: true` in the proxy's
  `config.yml`. On Paper or Spigot, set `settings.bungeecord: true` in
  `spigot.yml` and disable Velocity forwarding if enabled. Legacy forwarding
  trusts the proxy connection, so the backend network restriction is
  essential. [Legacy forwarding guide](https://docs.papermc.io/velocity/player-information-forwarding/#configuring-legacy-bungeecord-compatible-forwarding)

Restart each backend after updating its settings. Keep the forwarding secret
private and update every Velocity backend when you rotate it.

## Edit routing and plugins

Use **Files** to edit `velocity.toml` or `config.yml` in the data root, then
restart the proxy. In Velocity, declare your backends and fallback order in
`[servers]` and map hostnames in `[forced-hosts]`. In Waterfall and BungeeCord,
declare your backends in `servers` and set `priorities` and `forced_hosts` on
the listener. Keep the listener on TCP 25565 so the Gameplane service and
health probes reach it.

**Initial lobby address** only takes effect when the active routing file is
missing. Gameplane refreshes the seed files under `gameplane-defaults/` on pod
startup. Use the live file for routing changes. Waterfall and BungeeCord share
`config.yml`, while Velocity uses `velocity.toml`.

In **Mods**, upload a proxy-compatible `.jar` or install one from an allowed
release URL, then restart. The active proxy type gets its own plugin volume,
including plugin settings. Gameplane retains each volume when you change types.
Back up the plugin volumes separately from the primary GameServer backup,
which covers the routing files and Velocity forwarding secret.

Waterfall uses the archived `1.21` build `615`. On startup the launcher
downloads its six default core modules from PaperMC as needed and verifies
their checksums. If startup reports a checksum mismatch in an installed core
JAR, remove that JAR and restart to fetch a fresh copy. Waterfall and
BungeeCord keep separate core modules in their plugin volumes. When importing
existing proxy data, move `modules/` and `modules.yml` out of the data root
before starting the Gameplane proxy so it can initialize these paths for the
selected type. [PaperMC build metadata](https://fill.papermc.io/v3/projects/waterfall/versions/1.21/builds/615)

## Console and updates

Use **Console** to run commands supported by the selected proxy. Use the
backend GameServers for player statistics and idle detection.

Gameplane generates the RCON password under the `password` key in the
Kubernetes Secret `<name>-rcon` and uses RCON for Console and graceful
shutdown. The image writes the password to `plugins/velocircon/rcon.yml`
for Velocity or `plugins/bungee-rcon/config.yml` for Waterfall and BungeeCord.
It writes these files only when absent. After rotation or a restore, make
sure the Secret and the active plugin configuration use the same password,
then restart. Repeat for each retained plugin volume before switching back
to its proxy type. Treat these plugin files and backups as credentials.

The image digest pins the launcher and Java 25 runtime. The launcher resolves
and downloads the selected proxy and RCON plugin from upstream. Velocity and
BungeeCord build selection can change independently of the image digest.
Check upstream availability and client, backend, and plugin compatibility
before switching types. [itzg/mc-proxy documentation](https://github.com/itzg/docker-mc-proxy/tree/2026.11.1)
