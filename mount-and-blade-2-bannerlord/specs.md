# Gameplane Module Specification: Mount & Blade II: Bannerlord

## 1. Purpose & Scope

- **Game**: Mount & Blade II: Bannerlord
- **Module Slug**: `mount-and-blade-2-bannerlord`
- **Role**: Dedicated server module package for Gameplane.
- **Description**: Medieval combat simulation and roleplay multiplayer server. Provides match-based skirmish and siege modes with PTY-attached server administration.

---

## 2. Container Image & Architecture

- **Base Image**: `ghcr.io/gameplanepanel/gameplane/mount-and-blade-2-bannerlord:latest@sha256:ac4796548429fce3bf1990839b75002f08ee8d6c11260bc4a26329f5a7d93717`
- **Architecture**: `linux/amd64`
- **Image Source**: Built from `images/games/mount-and-blade-2-bannerlord/` in the main Gameplane repository on the shared SteamCMD base.
- **Runtime Model**: Linux-native / Wine .NET 6 TaleWorlds dedicated server binary.
- **User & Execution Context**: UID `10000`, GID `10000`, working directory `/data`.

---

## 3. Network Ports & Protocols

Declared ports under `spec.ports`:

| Port Name | Container Port | Protocol | Usage / Purpose |
|---|---|---|---|
| `game` | `7210` | `UDP` | Client game traffic |
| `query` | `7211` | `UDP` | Server browser and A2S query discovery |

---

## 4. Storage & Persistence Layout

- **Mount Path**: `/data`
- **Default Sizing**: `20Gi`
- **Persisted Content**:
  - Downloaded server binaries and TaleWorlds modules
  - Match configuration files (`tdm_config.txt`, `siege_config.txt`)
  - Server tokens and authentication credentials
- **Non-Shadowing Invariant**: The volume holds the whole install, so nothing in the image is shadowed (the image ships only SteamCMD and the entrypoint).

---

## 5. Administration & Remote Console (RCON)

- **Protocol**: `none`
- **Console Mode**: `pty`
- **Authentication**: N/A (interactive stdin console).
- **Command Support**: TaleWorlds CLI console commands issued via stdin.

---

## 6. Modding & Workshop Integration

- **Modding Framework**: Bannerlord Module XMLs and sub-modules
- **Mod Directory Path**: `Modules`
- **Workshop Synchronization**: Manual file drop or volume mount.

---

## 7. Lifecycle & Graceful Shutdown

- **Stop Command Sequence (`spec.capabilities.lifecycle.stop`)**: `[]` (Stateless match-based gameplay; processes terminate cleanly on SIGTERM).
- **Signal Handling**: Container intercepts `SIGTERM` and shuts down the active match cleanly.

---

## 8. Key Invariants & Security

- **User Matching**: `spec.security.runAsUser: 10000` matches image user.
- **Environment**: `HOME=/home/gameserver` is baked into the image (no `spec.env` entry needed).
- **Filesystem Permissions**: `spec.security.fsGroup: 10000` ensures write permission on `/data`.

---

## 9. References & Upstream Documentation

- Official Game Documentation: https://www.taleworlds.com/
- Steam Dedicated Server AppID: `1863440`
