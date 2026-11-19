# Gameplane Module Specification: Minecraft (Java Edition)

## 1. Purpose & Scope

- **Game**: Minecraft: Java Edition
- **Module Slug**: `minecraft-java`
- **Version**: 2.13.0 (minimum Gameplane 0.5.0)
- **Role**: GameTemplate for Minecraft Java servers, backed by the community `itzg/minecraft-server` image.

---

## 2. Container Image & Architecture

- **Images**: `itzg/minecraft-server` tagged by Java runtime. `java8-multiarch` for Minecraft 1.16.5 and older, `java17` for 1.18.2 to 1.20.x, `java21` for 1.21.x, `java25` for newer versions. The tag selects the runtime only; `TYPE` and `VERSION` select the server software.
- **Image override**: `GameServer.spec.image` replaces the tag for one server.

---

## 3. Network Ports & Protocols

| Port Name | Container Port | Protocol | Advertised | Usage / Purpose |
|---|---|---|---|---|
| `game` | 25565 | TCP | yes | Game traffic |
| `rcon` | 25575 | TCP | no | Agent console, moderation, backup quiesce, metrics (pod network only) |

---

## 4. Mod Registries (`spec.capabilities.mods.registry.providers`)

The Mods tab and the Modpacks tab read the same provider list.

| Provider | Mods tab | Modpacks tab | Key | Pin env (version) |
|---|---|---|---|---|
| `modrinth` (default) | yes | yes | none | `MODRINTH_VERSION` |
| `curseforge` | yes | yes | `CF_API_KEY` (see section 5) | `CF_FILE_ID` |
| `hangar` | yes | no | none | n/a |
| `ftb` | no (`modpacksOnly: true`) | yes | none | `FTB_MODPACK_VERSION_ID` |

### CurseForge provider

- `curseforgeGameID: 432` (Minecraft).
- Modpacks: `TYPE=AUTO_CURSEFORGE`, `CF_SLUG` (pack), `CF_FILE_ID` (pinned file), `CF_DOWNLOADS_REPO=/data/downloads`.
- `missingFilesPath: MODS_NEED_DOWNLOAD.txt`: files whose authors block third-party downloads are listed here and in the Modpacks tab. The admin places them in `/data/downloads` and restarts.
- `needsKeyImageTags: [java8-multiarch, java8]`: these images have no built-in key.

### FTB provider

- `TYPE=FTBA`, `FTB_MODPACK_ID`, pinned by `FTB_MODPACK_VERSION_ID`.
- Keyless. Modpacks only.

### Modrinth provider

- `TYPE=MODRINTH`, `MODRINTH_MODPACK` (slug), pinned by `MODRINTH_VERSION`.
- `adoptVersionFile: { path: .modrinth-modpack-manifest.json, field: versionId }` lets Gameplane adopt packs installed before version pinning.

---

## 5. CurseForge API Key Handling

- The CurseForge API key is stored through the panel's mod registry API. Without it, the CurseForge provider is hidden.
- Images with a built-in key (`java17` and newer) need nothing more.
- Images without one (`java8`, `java8-multiarch`) get CurseForge packs only while key sharing is on. Sharing is opt-in (off by default) and is set through the API by adding the `gameplane.local/share-with-game-servers: "true"` annotation to the managed Secret `gameplane-modreg-curseforge`. There is no dashboard switch yet.
- While sharing is on, the operator gives each affected server a server-owned Secret holding the admin key. The game container reads it as `CF_API_KEY` via `valueFrom.secretKeyRef`. The Secret follows key rotation and is removed when the admin key is removed or sharing is turned off.
- The key is never written into GameServer env as plain text, into logs, or into API responses.

---

## 6. Storage & Persistence Layout

- **Data PVC**: 10 GiB default, mounted at `/data` (override with `GameServer.spec.storage`).
- **Downloads**: `/data/downloads` (CurseForge blocked-file drop folder).
- **Mod volumes**: one PVC per (version, loader) pair, provisioned on demand and retained across version switches.
- **World data**: `/data/world`, `world_nether`, `world_the_end`.

---

## 7. Startup & Probes

- Readiness: `mc-health`, initial delay 30s.
- Liveness: `mc-health`, initial delay 120s.
- First boot downloads the server jar, and any modpack, before the game starts. That output appears in the Logs tab's container output source.
