# Arma Reforger

Arma Reforger dedicated server package for Gameplane. Runs on Bohemia Interactive's Enfusion engine with interactive PTY stdin console, persistent profile and saves, and Steam Workshop modding support.

Image: `ghcr.io/acemod/arma-reforger` (https://github.com/acemod/docker-reforger), the ACE team's community image. It runs as root by design, and SteamCMD installs the server into `/reforger` on every start.

## Install

```sh
kubectl apply -f modules/arma-reforger/template.yaml
```

## Console

No RCON protocol. The **Console** tab attaches directly to container stdin/stdout (pty) for administrative commands. Server stop issues `save` prior to pod termination.

## SteamCMD Login

Most dedicated servers allow anonymous SteamCMD download. If an authenticated Steam login is required to pull specific game builds or workshop dependencies, provide credentials in `STEAM_USER` and `STEAM_PASSWORD`.

## Ports

| Name | Port | Protocol | Advertised | Purpose |
| ---- | ---- | -------- | ---------- | ------- |
| `game` | 2001 | UDP | yes | Client gameplay |
| `query` | 17777 | UDP | yes | Steam / A2S query |

## Storage

Persistent storage is mounted at `/reforger` (30 GiB default). The server install, `Configs/`, `profile/`, and `workshop/` all live on the volume, so world state, player profiles, and downloaded Workshop mods persist across container restarts.

## Sample

See [`samples/gameserver.yaml`](samples/gameserver.yaml) for a deployment example.
