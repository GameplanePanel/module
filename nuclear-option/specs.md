# Gameplane Module Specification: Nuclear Option (Dedicated)

## 1. Purpose & Scope

- **Game**: Nuclear Option (Unity, multiplayer tactical team-based game)
- **Module Slug**: `nuclear-option`
- **Role**: Dedicated server module package for Gameplane.
- **Source of verified facts**: `specs/002-nuclear-option-ip-pool/spec.md` (Verification Required Before Implementation, Claims 1-5) and `specs/002-nuclear-option-ip-pool/contracts/nuclear-option-remote-command.md`, both checked against a live server on 2026-08-22. Items not covered by that evidence are marked **UNVERIFIED**.

---

## 2. Container Image & Architecture

- **Image**: `ghcr.io/gameplanepanel/gameplane/nuclear-option@sha256:acaeb3b7f0ab55bf6efe678b74745ed1a437ff97bf6d52cd26844efd28c13ce6`
- **Build**: Built by Gameplane from `images/games/nuclear-option` and published, cosign-signed, by Gameplane's `images.yaml`. The module does not depend on a third-party server image.
- **Game install**: SteamCMD, anonymous login, app `3930080` (`+login anonymous +app_update 3930080 validate`). Anonymous download succeeds without owning the base game (app `2168680`) (Claim 1).
- **Architecture**: `linux/amd64` only. The binary `NuclearOptionServer.x86_64` is a native Linux x86-64 executable, not Proton/WINE. No arm64 support.
- **Installed footprint**: 891 MB (Claim 1, spec FR-002 amendment).
- **User & Execution Context**: Runs as non-root user `gameserver`, uid/gid `10000`. `spec.security.runAsUser: 10000`, `runAsGroup: 10000`, `fsGroup: 10000` are set in the template (required, because the image is non-root).
- **Update on boot**: `UPDATE_ON_BOOT=true`. SteamCMD installs or updates the server on every pod start.

---

## 3. Network Ports & Protocols

Observed on a running server (netstat, Claim 2, 2026-08-22):

| Port | Protocol | Bind | Usage | Status |
|---|---|---|---|---|
| `7778` | UDP | all interfaces | Query | **Confirmed bound** |
| `45793` | UDP | ephemeral | Not a module port | Observed; not declared |
| `7779` | TCP | `127.0.0.1` only | Remote-command protocol | **Confirmed**, loopback only |
| `7777` | UDP | - | Assumed game join port | **NOT bound** (no listening socket observed) |

Declared under `spec.ports` in `template.yaml`:

| Name | Container Port | Protocol | Advertised | Notes |
|---|---|---|---|---|
| `game` | `7778` | UDP | yes | Port 7778 is confirmed bound, but the observed role is query, not game join. See Known Limitations. |
| `rcon` | `7779` | TCP | no | Loopback only. Never advertised. |

Game join path:

- The server logs `SteamGameServer.LogOnAnonymous` and `Set Advertise Server: True`. Player traffic appears to route through Steam's game-server networking, not a raw UDP 7777 socket.
- **UNVERIFIED**: a real client join. No connected-client join test has been run.

Remote-command enablement (protocol contract, Enablement section):

- Launch flag `-ServerRemoteCommands [port]`. Disabled by default. Without a port argument, the default is TCP 7779.
- The template sets `REMOTE_COMMANDS_ENABLED=true`.
- Log line on start: `[CommandLineArgParser] Starting remote command server on port 7779`.

---

## 4. Storage & Persistence Layout

- **Mount Path**: `/data` (the SteamCMD install target and all persistent state).
- **Default Sizing**: `2Gi`. The 30 GB figure in the original spec is withdrawn (Claim 1 / FR-002 amendment: 891 MB installed).
- **Persisted Content**:
  - Server install (`NuclearOptionServer.x86_64` and game files).
  - Rendered config: `/data/DedicatedServerConfig.json`, re-rendered from the template on every pod start.
  - Mission files: `/data/NuclearOption-Missions/`.
  - Ban list: configured as the relative path `ban_list.txt` (`BanListPaths`). **Verified 2026-10-11**: the server's working directory is `/data`, so it resolves to `/data/ban_list.txt`, on the volume. **The server never creates this file.** On a fresh install `banlist-add` logs `[AllowBanList] [Error] File does not exist: ban_list.txt` and the ban is held in memory only; nothing is written. Once the file exists (created empty or with IDs), `banlist-add` appends one Steam ID per line (`Appending Steam <id> to ban_list.txt`) and `banlist-remove` deletes the line. Today bans made on a fresh server do not survive a restart or a backup/restore until the file exists. The module does not create it; this needs a template or entrypoint change (listed for the maintainer, not made here).
  - Mission state: no mission-state file was observed. `/data/NuclearOption-Missions/` did not exist on a fresh server, and `set-next-mission` changes nothing on disk. The next-mission override is in memory and does not survive a restart.
  - Logs: not on the volume (see section 6).
- **Backups**: Gameplane backup and restore capture the whole `/data` volume (FR-013). No module-specific backup tooling. **Round-trip verified 2026-10-11** with the stock `Backup`/`Restore` CRs and a restic REST repo: backup of the 936 MB volume completed in 9 s; the restore suspended the server, restored, and restarted it in about 5 s. `DedicatedServerConfig.json` and a planted `ban_list.txt` were wiped, then came back with SHA-256 sums identical to before the backup. Mission state could not be checked because none exists on disk. The restored pod then started normally.

---

## 5. Configuration

Rendered into `DedicatedServerConfig.json` from `configSchema`:

| Setting | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `SERVER_NAME` | string | `A Gameplane Nuclear Option server` | required, 1-64 chars | Maps to `ServerName`. |
| `SERVER_PASSWORD` | password | empty | none | Maps to `Password`. Empty means an open server. |
| `MAX_PLAYERS` | int | `16` | 4-64 (Gameplane-side range) | Maps to `MaxPlayers`. The server-enforced limit is **UNVERIFIED**. Default 16 is what the live server reported. |
| `MISSION_ROTATION` | enum | `0` | `0` or `1` | Maps to `RotationType`. Semantics **UNVERIFIED**; `0` appears to be sequential. The spec's `sequence`/`random` naming is not used because the config file's `RotationType` is numeric. |

Config fields verified against the live server (contract, Live Protocol Verification): `ServerName` (string), `Password` (string), `MaxPlayers` (integer, default 16), `Port` and `QueryPort` (`{IsOverride, Value}` objects), `BanListPaths` (array), `MissionDirectory` (string), `MissionRotation` (array of mission objects).

The template sets the mission rotation to `BuiltIn/Escalation` and `BuiltIn/Terminal Control`, each with `MaxTime` 7200.0.

Config-path override: the `-DedicatedServer <path/to/config.json>` flag sets the config location (Claim 5). The template sets `DEDICATED_SERVER_CONFIG=/data/DedicatedServerConfig.json`.

---

## 6. Logs

- **Verified location** (Claim 5): `./logs/server-<timestamp>.log`, written when the server is started with the `-logFile` flag through `RunServer.sh`. Format is plain text.
- **Gameplane image log path** (verified 2026-10-11): the image entrypoint (`containers/games/nuclear-option/entrypoint.sh`) execs `NuclearOptionServer.x86_64 -batchmode -nographics -ServerRemoteCommands -DedicatedServer /data/DedicatedServerConfig.json` directly as PID 1. It does not use `RunServer.sh` and passes no `-logFile`, so the Unity log goes to **stdout only** (`kubectl logs <pod> -c game`). Format: plain text, one line per event, prefixed with seconds since start and a `[Component]` tag (for example `3.484: [DedicatedServerManager] Starting run loop`). The first lines of the stream are the SteamCMD install output.
- **No game log file exists on `/data`.** No `*.log` or `./logs/` directory was found on the volume, so game logs are not in the backup scope. Steam's own client logs go to `/home/gameserver/.local/share/Steam/logs/`, which is outside the volume and is lost on pod restart.

---

## 7. Readiness, Probes & Startup

- **Readiness signal** (Claim 4, resolved): the log line `[DedicatedServerManager] Waiting for Players before loading next map` appears about 3.9 s after startup and marks the point the server accepts connections.
- **Probes in template**: all three probes (startup, readiness, liveness) are exec probes running `timeout 2 nc -z 127.0.0.1 7779`. They check the remote-command port, not the log line.
- **Observed defect (2026-10-11): the probes cannot succeed.** The game image has `timeout` but no `nc`. Every probe fails with `timeout: failed to execute process: No such file or directory`. On kubelab the pod stayed `1/2` (agent ready, game container never `started`), the GameServer stayed in phase `Starting`, and kubelet restarted the game container once the startup budget ran out (about 20 minutes). The server itself ran normally throughout and answered on 7779. The log marker above did appear. Fixing this needs a template or image change (for example a probe that does not depend on `nc`); none was made here.
- **Why not tcpSocket**: the server binds `127.0.0.1:7779` only. Kubelet tcpSocket probes connect from the node to the pod IP, so they cannot reach a loopback-only socket. Exec probes run inside the pod and avoid this.
- **Startup budget**: first boot downloads about 891 MB. `initialDelaySeconds` 30, `periodSeconds` 15, `failureThreshold` 80 give about 20 minutes.
- **Liveness**: `periodSeconds` 30, `failureThreshold` 5.
- **Graceful stop**: no remote shutdown/stop/quit/exit command is among the 20 registered commands. The image runs the game as PID 1 so SIGTERM reaches it. The module relies on the game's own graceful shutdown.

---

## 8. Administration & Remote Console

- **Protocol**: `nuclearoption` (agent `parseNuclearOptionCommand`).
- **Transport**: TCP, length-prefixed JSON.
  - Request: 4-byte LE length + `{"name": "...", "arguments": [...]}`.
  - Response: 4-byte LE status + 4-byte LE body length + optional JSON body.
- **Authentication**: **none**. No password, no handshake. The template sets `rcon.authentication: false`. The port is loopback only, so only pod-local clients can reach it.
- **Status codes**: 2000 success; 4000 bad request; 4001 bad header; 4002 bad length; 4003 JSON error; 4004 unknown command; 4005 bad arguments; 5000 internal error; 5001 command error; 5002 config error.

### 8.1 Actions declared in `capabilities.actions`

Argument parsing (agent): the first space-separated word is the command name. For `send-chat-message` the whole remainder is one argument. For every other command the remainder is split on spaces.

| Action id | Command rendered | Arguments | Notes |
|---|---|---|---|
| `broadcast` | `send-chat-message {{message}}` | 1 string (whole message) | Verified argument shape. |
| `set-next-mission` | `set-next-mission {{group}} {{name}} {{maxTime}}.0` | 3: Group (string), Name (string), MaxTime (float seconds) | Server rejects a single argument with 4005 (`Expected Arguments [string Group, string Name, float MaxTime]`). Example: `BuiltIn Escalation 3600.0`. Mission names with spaces cannot be sent (space splitting). |
| `set-time-remaining` | `set-time-remaining {{seconds}}.0` | 1: seconds (float) | Requires confirm in the dashboard. Response body **UNVERIFIED**. Integer form without `.0` **UNVERIFIED**; the template sends the float form shown in the contract. |
| Players: list | `get-player-list` | none | Response `{"Players": [...]}`. Verified empty-list shape only. |
| Players: kick | `kick-player {{Player}}` | 1: Steam ID | Returns 2000 even for unknown Steam IDs. |
| Players: ban | `banlist-add {{Player}}` | 1: Steam ID | Returns 2000 even for unknown Steam IDs. |
| Players: unban | `banlist-remove {{Player}}` | 1: Steam ID | Returns 2000 even for unknown Steam IDs. |

Other registered commands (not declared as actions): `update-ready`, `reload-config`, `get-mission-time`, `get-mission`, `get-server-id`, `get-player-list`, `set-time-remaining`, `set-next-mission`, `kick-player`, `unkick-player`, `clear-kicked-player`, `clear-kicked-players`, `banlist-reload`, `banlist-add`, `banlist-remove`, `banlist-clear`, `get-mission-rotation`, `set-mission-rotation`, `clear-next-mission`. The contract gives their argument shapes.

### 8.2 Player list

- Verified: wrapper key `Players` (capital P). Empty list observed.
- Per-entry fields `steamId` and `faction` are documented by the publisher. The per-entry shape was **not** confirmed with a connected player (UNVERIFIED).
- Display names are not on the wire. The API server resolves them through the optional Steam Web API lookup (`ISteamUser/GetPlayerSummaries/v2`) when a key is configured. Without a key, or if a lookup fails, the list shows the raw Steam ID. Moderation always uses the Steam ID.

---

## 9. Resource Requirements

- **Requests**: 2 CPU, 8 Gi memory. **Limits**: 4 CPU, 16 Gi memory. Source: spec FR-002 (2-4 cores, 8 GB minimum, 16 GB recommended).
- **Measured**: none under player load. These values are spec defaults, not measurements.
- **Disk**: 891 MB installed, 2 Gi volume.

---

## 10. Key Invariants & Security

- **User matching**: image runs as uid/gid `10000`. `spec.security.runAsUser` must be set to match.
- **Filesystem**: `fsGroup: 10000` lets the non-root user write the SteamCMD install into `/data`.
- **Remote-command port**: no authentication and loopback only. Do not expose TCP 7779 outside the pod. The template does not advertise it.
- **Moderation identifiers**: Steam IDs only.

---

## 11. Known Limitations

- **Join path unverified**: no real client has joined through the Gameplane-deployed server. UDP 7777 is not bound; join is expected through Steam's routing.
- **Port 7778 role**: confirmed bound and observed as the query port. The template still declares it as the advertised `game` port. Whether the game-join path needs a different port is an open item.
- **Kick and ban feedback**: `kick-player`, `banlist-add` and `banlist-remove` return 2000 for unknown Steam IDs. Success does not confirm that the target existed. Verify with `get-player-list` or the ban list.
- **Mission names with spaces**: the agent splits arguments on spaces, so a name such as `Terminal Control` cannot be passed to `set-next-mission`. Names without spaces work.
- **Mission list**: valid group and name values beyond the documented examples (`BuiltIn`, `Escalation`) are **UNVERIFIED**. The `MISSION_LIST` field is not in the module; no JSON mission field is added.
- **Mission rotation**: `MISSION_ROTATION` semantics are **UNVERIFIED**.
- **MAX_PLAYERS**: the server-enforced limit is **UNVERIFIED**. Gameplane accepts 4-64.
- **Set-time-remaining**: response body **UNVERIFIED**.
- **Player list entry shape**: `faction` and `steamId` fields are documented; per-entry shape is unverified with a connected player (no client was available on 2026-10-11 either).
- **Chat**: `send-chat-message` returned 2000 but the server logged a `NullReferenceException` with no players connected. Whether chat works with a player connected is **UNVERIFIED**.
- **Set-next-mission validation**: the server answers 2000 for any group and name, including nonexistent ones. The response cannot confirm the mission exists, and the override is not persisted (section 4).
- **Ban persistence**: bans are written to disk only if `/data/ban_list.txt` already exists (section 4).
- **Probes**: the exec probes use `nc`, which the image lacks; the pod never reports Ready (section 7).
- **Steam Web API display names (T127)**: **not observed**. The moderation walk with and without the `api.steam.apiKeySecretRef` Secret needs a connected player, and none was available. The expected behaviour (names resolved with the Secret; raw Steam IDs without it, no error, within 5 s, SC-004) is unconfirmed.
- **Architecture**: x86_64 only.
- **Resource figures**: spec defaults, not measured under load.

---

## 12. Verification Record (2026-08-22)

| Claim | Result | Evidence |
|---|---|---|
| 1. Dedicated server availability and platform | Resolved | Anonymous SteamCMD install of app 3930080 without app 2168680. Native Linux `NuclearOptionServer.x86_64`. 891 MB. |
| 2. Network ports | Amended | TCP 127.0.0.1:7779 confirmed. UDP 7778 bound. UDP 7777 not bound. |
| 3. Remote-command protocol | Resolved | Length-prefixed JSON framing; status codes 2000/4003/4004/4005 confirmed. `set-next-mission` takes 3 arguments. Kick, ban and unban return 2000 for unknown IDs. |
| 4. Readiness signal | Resolved | `[DedicatedServerManager] Waiting for Players before loading next map` at about 3.9 s. |
| 5. Log location and format | Superseded for the Gameplane image | `./logs/server-<timestamp>.log` applies to the vendor `RunServer.sh`. The Gameplane image logs to stdout only (section 6, 2026-10-11). |

### Config validation matrix (2026-10-11, T128)

Run on kubelab against a server from the repo template (minus `spec.rcon.authentication`, which the cluster's older CRD rejects). One GameServer per case; `status.phase` and the `Ready` condition read back.

| `spec.config` | Result |
|---|---|
| `SERVER_NAME` 65 characters | `Failed` within 1 s: `config field "SERVER_NAME" must be at most 64 characters` |
| `SERVER_NAME` empty | `Failed`: `required config field "SERVER_NAME" has no value and no default` |
| `MAX_PLAYERS: "3"` | `Failed`: `config field "MAX_PLAYERS" must be at least 4` |
| `MAX_PLAYERS: "65"` | `Failed`: `config field "MAX_PLAYERS" must be at most 64` |
| `MAX_PLAYERS: "abc"` | `Failed`: `config field "MAX_PLAYERS": "abc" is not an integer` |
| `MISSION_ROTATION: "2"` | `Failed`: `config field "MISSION_ROTATION": "2" is not one of [0, 1]` |
| unknown key `BOGUS_FIELD` | `Failed`: `unknown config keys BOGUS_FIELD: template … accepts [SERVER_NAME, SERVER_PASSWORD, MAX_PLAYERS, MISSION_ROTATION]` |
| `SERVER_NAME: He said "hi" \ back`, `SERVER_PASSWORD: p"w\d` | Valid. Rendered into `DedicatedServerConfig.json` with correct JSON escaping (`"He said \"hi\" \\ back"`); the server started and advertised the name unchanged |

All seven invalid cases were rejected by the operator before any pod was created (`pods … NotFound`), with the field and constraint named. No crash-loop or hung state. The mission-name case is skipped (`MISSION_LIST` was dropped). The CRD itself does not validate (`spec.config` is a string map), so the rejection comes from the reconciler, not at `kubectl apply`.

---

## 13. References & Upstream Documentation

- Remote-command contract: `specs/002-nuclear-option-ip-pool/contracts/nuclear-option-remote-command.md` (publisher documentation, Shockfront Studios Nuclear Option Server Tools).
- Feature spec: `specs/002-nuclear-option-ip-pool/spec.md`.
- Agent parser: `agent/internal/rcon/nuclearoption.go`.
- Game homepage: https://www.nuclearoption.com/
