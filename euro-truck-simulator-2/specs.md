# Gameplane Module Specification: Euro Truck Simulator 2

## 1. Purpose & Scope

- **Game**: Euro Truck Simulator 2
- **Module Slug**: `euro-truck-simulator-2`
- **Role**: Dedicated server module package for Gameplane.
- **Description**: Dedicated convoy multiplayer server for Euro Truck Simulator 2. Features PTY-driven console management, Steam server logon token configuration, and diagnostic idle for unconfigured deployments.

---

## 2. Container Image & Architecture

- **Base Image**: `ghcr.io/gameplanepanel/gameplane/euro-truck-simulator-2:latest@sha256:3296f2b444b1924933256e7e965ab96ba737c514542064db6a634759869e5e6d`
- **Architecture**: `linux/amd64`
- **Runtime Model**: Linux 64-bit standalone dedicated server binary (`eurotrucks2_server`) installed at start into the volume with SteamCMD (app `1948160`, anonymous) and managed by Gameplane supervisor script. The entrypoint exits non-zero if the binary is missing after install.
- **User & Execution Context**: UID `10000`, GID `10000` (SteamCMD base image user), working directory `/data`.

---

## 3. Network Ports & Protocols

Declared ports under `spec.ports`:

| Port Name | Container Port | Protocol | Usage / Purpose |
|---|---|---|---|
| `game` | `27015` | `UDP` | Primary client convoy game traffic |
| `query` | `27016` | `UDP` | Steam server browser query |

---

## 4. Storage & Persistence Layout

- **Mount Path**: `/data` (`GP_DATA_DIR`)
- **Default Sizing**: `10Gi`
- **Persisted Content**:
  - Installed dedicated server (`bin/linux_x64/`)
  - Convoy configuration files (`profile/server_config.sii`)
  - Server packages, saves, and session cache
- **Non-Shadowing Invariant**: The server is installed into the mounted volume itself, so nothing the entrypoint needs is shadowed by the mount.

---

## 5. Administration & Remote Console (RCON)

- **Protocol**: `none`
- **Console Mode**: `pty`
- **Authentication**: N/A (interactive terminal console).
- **Command Support**: Standard ETS2 server console commands issued via stdin.

---

## 6. Modding & Workshop Integration

- **Modding Framework**: SCS packages and Steam Workshop convoy mods
- **Mod Directory Path**: Mod packages placed in profile directory
- **Workshop Synchronization**: Handled via convoy session sync.

---

## 7. Lifecycle & Graceful Shutdown

- **Stop Command Sequence (`spec.capabilities.lifecycle.stop`)**:
  ```yaml
  capabilities:
    lifecycle:
      stop:
        - "exit"
  ```
- **Signal Handling**: Issues `exit` to stdin and catches `SIGTERM` in `entrypoint.sh` for clean termination.

---

## 8. Key Invariants & Security

- **User Matching**: `spec.security.runAsUser: 10000` matches image user.
- **Environment**: `spec.env` defines `GP_DATA_DIR: /data`.
- **Filesystem Permissions**: `spec.security.fsGroup: 10000` guarantees write permissions.
- **Diagnostic Idle**: Automatically enters idle state with step-by-step instructions if `SERVER_LOGON_TOKEN` is missing (FR-013). The entrypoint touches `/tmp/gp-diagnostic-idle`, which only the startup probe accepts, so the idle is not restarted; readiness still requires the bound UDP port.

---

## 9. References & Upstream Documentation

- Official Game Documentation: https://eurotrucksimulator2.com/
- Steam Dedicated Server AppID: `1948160`
