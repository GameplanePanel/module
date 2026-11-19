# `minecraft-java` module

Gameplane GameTemplate for Minecraft: Java Edition.

## Install

```sh
kubectl apply -f modules/minecraft-java/template.yaml
```

The template is cluster-scoped — install once per cluster. The Gameplane
dashboard will then show Minecraft in the catalog.

## Version & loader choice

The New Server wizard shows a version picker populated from `spec.versions`
— e.g. `26.3 · Paper`, `1.21.11 · NeoForge`, `Latest · Vanilla`. Each entry
selects the [`itzg/minecraft-server`](https://github.com/itzg/docker-minecraft-server)
image plus the `TYPE`/`VERSION` env that pick the server software, so you
never set those by hand. To pin an exact image build, set
`GameServer.spec.image` (Settings → Image override).

## Mod manager

Mods and plugins are managed from the **Mods** tab. Each *(version + loader)*
combination has its own volume, so a Paper plugin set and a Forge mod set
never collide and survive switching versions. Plugin loaders
(Paper/Spigot/Bukkit/Purpur) store under `plugins/`; mod loaders
(Forge/NeoForge/Fabric/Quilt) under `mods/`. Vanilla servers have no mod loader, so
the tab is hidden for them. Installs are allowed from Modrinth, CurseForge,
Hangar, and GitHub (max 512 MiB), subject to the agent's SSRF guard.

The Mods tab's **Search registry** mode browses [Modrinth](https://modrinth.com)
filtered to the server's active loader and game version, so you can find and
one-click install a mod or plugin by name without hunting for a URL. The
chosen file downloads through the same allowlist (Modrinth's CDN is listed).
**From URL** install remains available for anything not on Modrinth.

## Modpacks (2.13.0)

The **Modpacks** tab installs a whole modpack onto a server. Modrinth,
CurseForge and FTB packs are listed; the pack is pinned to a version and
installed on boot by the game image, so one modpack applies per server.
Changing the pinned version is a server update, and Gameplane adopts packs
that were installed before version pinning existed. FTB packs are modpacks
only and do not appear in the Mods tab.

Each provider pins its pack by version: CurseForge by file ID
(`CF_FILE_ID`), Modrinth by version ID (`MODRINTH_VERSION`) and FTB by
version ID (`FTB_MODPACK_VERSION_ID`).

### What admins need for CurseForge

- **API key.** Store a CurseForge API key in the panel's admin config. Without
  one, the CurseForge provider is hidden.
- **Minecraft 1.16.5 and older (`java8` images).** The `java8-multiarch` and
  `java8` images have no built-in CurseForge key. CurseForge packs for these
  versions are offered only while **Share the CurseForge key with game
  servers** is on in the admin settings (off by default). With sharing on,
  each server gets its own server-owned copy of the key, passed to the game
  container as `CF_API_KEY`. The copy follows key rotation and is removed when
  the admin key is removed or sharing is turned off. The key never appears in
  GameServer env as plain text, in logs, or in API responses.
- **Images for 1.18.2 and newer** (`java17`, `java21`, `java25`) ship a
  built-in key, so sharing is not needed for them.

### Blocked downloads

Some CurseForge mod authors do not allow third-party downloads. Gameplane
lists those files in the Modpacks tab. Upload them to the server's
`downloads/` folder (`/data/downloads`, the `CF_DOWNLOADS_REPO` path on the
data volume), then restart the server to finish the install.

### FTB

FTB packs need no key. They use the `ftb` provider, which is modpacks only.

Modpacks need minimum Gameplane 0.5.0.

## JVM startup settings (2.12.0)

Install the Gameplane CRDs and operator with support for `applyOnRestart`
before updating the catalog module to 2.12.0 (minimum Gameplane 0.4.1).
Adopting this template on a running server can restart it once. A server
using the OnRequest template policy can schedule that adoption. Once adopted,
saving or clearing heap sizes, extra JVM options or Aikar's flags leaves the
running game in place. Restart it when ready to use the new values.

Each empty heap field independently defaults to 75% of the container memory
limit, rounded down to whole MiB. A 4Gi limit gives 3072M for each automatic
field. To set the maximum to 2G, also set an initial heap of 2G or less.
Leave space for the JVM's non-heap allocations.

Fixed sizes such as `512M` and `2G` become `-Xms` and `-Xmx`. A value such
as `37.5%` selects the JVM's InitialRAMPercentage or MaxRAMPercentage mode.
`JVM_OPTS` and `JVM_XX_OPTS` pass space-separated arguments through to the
image. Set heap sizes in their dedicated fields so a later argument does
not override the preview. `USE_AIKAR_FLAGS` enables the image's own preset.

## Logs (including install)

itzg downloads the selected server jar on first boot; that output streams to
the **Logs** tab's *Container output* source, so you can watch the install
even before the game has started. Once running, the persistent logfile at
`/data/logs/latest.log` feeds the *Game log* toggle.

## Ports

| Name | Port  | Protocol | Advertised |
| ---- | ----- | -------- | ---------- |
| game | 25565 | TCP      | yes        |
| rcon | 25575 | TCP      | no         |

RCON stays inside the pod network — the Gameplane agent uses it for the
Console tab, player moderation, backup quiesce, and Overview metrics.

## Storage

Default data PVC is 10 GiB mounted at `/data` (override via
`GameServer.spec.storage`). Each version+loader mod volume is a separate PVC
the operator provisions on demand and retains across version switches.

## Backups

World data lives under `/data/world` (and `world_nether`, `world_the_end`
for vanilla). A backup of the whole `/data` volume restores the world; mod
volumes are separate PVCs.
