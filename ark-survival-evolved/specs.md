# Gameplane Module Specification: ARK: Survival Evolved

## 1. Purpose & Scope

- **Game**: ARK: Survival Evolved
- **Module Slug**: `ark-survival-evolved`
- **Role**: Dedicated server module package for Gameplane.
- **Description**: Dedicated multiplayer server for Studio Wildcard's ARK: Survival Evolved. Manages persistent world saves, multi-shard cluster transfers, and Source RCON administration.

---

## 2. Container Image & Architecture

- **Base Image**: `ghcr.io/valgulnecron/gameplane/ark-survival-evolved:latest@sha256:0000000000000000000000000000000000000000000000000000000000000000`
- **Architecture**: `linux/amd64`
- **Image Source**: Built from `images/games/ark-survival-evolved/` in the main Gameplane repository on the shared SteamCMD base.
- **Runtime Model**: SteamCMD Linux dedicated server (`ShooterGameServer`).
- **User & Execution Context**: UID 10000, GID 10000, working directory `/data`.

---

## 3. Network Ports & Protocols

Declared ports under `spec.ports`:

| Port Name | Container Port | Protocol | Usage / Purpose |
|---|---|---|---|
| `game` | 7777 | UDP | Primary gameplay traffic |
| `query` | 27015 | UDP | Steam A2S browser discovery |
| `rcon` | 27020 | TCP | Remote administrative console (Source RCON) |

---

## 4. Storage & Persistence Layout

- **Mount Path**: `/data`
- **Default Sizing**: `35Gi`
- **Persisted Content**:
  - Saved worlds, tribe data, and dinosaur entities (`SavedArks/`)
  - Server configuration files (`Config/LinuxServer/GameUserSettings.ini`)
  - Cross-server cluster transfers (`clusters/`)
- **Non-Shadowing Invariant**: The volume holds the whole install, so nothing in the image is shadowed (the image ships only SteamCMD and the entrypoint).

---

## 5. Administration & Remote Console (RCON)

- **Protocol**: `source`
- **Console Mode**: `rcon`
- **Authentication**: Password supplied via `RCON_PASSWORD`.
- **Command Support**: In-game moderation (`KickPlayer`, `BanPlayer`), world saving (`SaveWorld`), broadcasts (`ServerChat`).

---

## 6. Modding & Workshop Integration

- **Modding Framework**: Steam Workshop (`-automanagedmods`).
- **Mod Directory Path**: Managed within image install.

---

## 7. Lifecycle & Graceful Shutdown

- **Stop Command Sequence (`spec.capabilities.lifecycle.stop`)**:
  ```yaml
  capabilities:
    lifecycle:
      stop:
        - "SaveWorld"
        - "DoExit"
  ```
- **Signal Handling**: Server cleanly saves before terminating on `SIGINT`/`SIGTERM`.

---

## 8. Key Invariants & Security

- **User Matching**: `spec.security.runAsUser: 10000` matches image user.
- **Environment**: `HOME=/home/gameserver` is baked into the image (no `spec.env` entry needed).
- **Filesystem Permissions**: `spec.security.fsGroup: 10000` ensures volume read/write permissions.

---

## 9. References & Upstream Documentation

- ARK: Survival Evolved Dedicated Server: https://ark.wiki.gg/wiki/Dedicated_server_setup
- Steam Dedicated Server AppID: 376030
