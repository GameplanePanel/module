# Gameplane Module Specification: The Isle

## 1. Purpose & Scope

- **Game**: The Isle
- **Module Slug**: `the-isle`
- **Role**: Dedicated server module package for Gameplane.
- **Description**: Dedicated multiplayer server for The Isle, an open-world dinosaur survival game running on Unreal Engine.

---

## 2. Container Image & Architecture

- **Base Image**: `ghcr.io/valgulnecron/gameplane/the-isle:latest@sha256:0000000000000000000000000000000000000000000000000000000000000000`
- **Architecture**: `linux/amd64`
- **Image Source**: Built from `images/games/the-isle/` in the main Gameplane repository on the shared SteamCMD base.
- **Runtime Model**: SteamCMD / Unreal Engine Linux dedicated server.
- **User & Execution Context**: UID 10000, GID 10000, working directory `/data`.

---

## 3. Network Ports & Protocols

Declared ports under `spec.ports`:

| Port Name | Container Port | Protocol | Usage / Purpose |
|---|---|---|---|
| `game` | 7777 | UDP | Primary client gameplay traffic |
| `query` | 7778 | UDP | Server browser discovery and A2S_INFO query |
| `rcon` | 8888 | TCP | Remote administrative console (Source RCON) |

---

## 4. Storage & Persistence Layout

- **Mount Path**: `/data`
- **Default Sizing**: `25Gi`
- **Persisted Content**:
  - Saved dinosaur entities and world maps
  - Configuration files (`Game.ini`, `Engine.ini`)
  - Admin rosters and ban lists
- **Non-Shadowing Invariant**: The volume holds the whole install, so nothing in the image is shadowed (the image ships only SteamCMD and the entrypoint).

---

## 5. Administration & Remote Console (RCON)

- **Protocol**: `source`
- **Console Mode**: `rcon`
- **Authentication**: Password supplied via `RCON_PASSWORD`.
- **Command Support**: Standard UE4 console commands including `save`, `announce`, `kick`.

---

## 6. Modding & Workshop Integration

- **Modding Framework**: Steam Workshop / Unreal Engine custom assets.
- **Mod Directory Path**: Unset / baked in game install.

---

## 7. Lifecycle & Graceful Shutdown

- **Stop Command Sequence (`spec.capabilities.lifecycle.stop`)**:
  ```yaml
  capabilities:
    lifecycle:
      stop:
        - "save"
  ```
- **Signal Handling**: Dedicated server initiates state flush on `SIGINT`/`SIGTERM`.

---

## 8. Key Invariants & Security

- **User Matching**: `spec.security.runAsUser: 10000` matches image user.
- **Environment**: `HOME=/home/gameserver` is baked into the image (no `spec.env` entry needed).
- **Filesystem Permissions**: `spec.security.fsGroup: 10000` configured for volume ownership.

---

## 9. References & Upstream Documentation

- The Isle Server Hosting Guide: https://findtheisle.com/
- Steam Dedicated Server AppID: 412680
