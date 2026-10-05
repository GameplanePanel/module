# tModLoader

tModLoader dedicated server for modded Terraria gameplay, packaged as a Gameplane module.

**Image:** [`passivelemon/terraria-docker`](https://github.com/PassiveLemon/terraria-docker) (`tmodloader-latest` tag)

## Install

```sh
kubectl apply -f modules/tmodloader/template.yaml
```

## Mod Management

A fresh server starts the built-in empty `vanilla` modpack (no mods). The **Mods** tab manages `.tmod` files in that pack, under `/opt/terraria/config/ModPacks/vanilla/Mods`; a mod loads once its name is listed in that folder's `enabled.json`. To run another modpack, put it under `/opt/terraria/config/ModPacks/<name>/Mods` (with its `enabled.json`) and set **Active modpack** (`MODPACK`) to `<name>`. Installs are allowed from GitHub release archives (max 512 MiB).

## Console (PTY)

Terraria engines do not provide an RCON TCP port. The **Console** tab attaches directly to the container's stdin/stdout (pty) using the kubelet pod-attach API. Stop sequence issues `exit` to trigger world flushing before shutdown.

## Ports

| Name | Port | Protocol | Advertised | Purpose |
| ---- | ---- | -------- | ---------- | ------- |
| `game` | 7777 | TCP | yes | Primary game traffic |

## Storage

Storage is mounted at `/opt/terraria/config` (4 GiB default), holding:
- World files (`Worlds/`)
- Modpacks (`ModPacks/<name>/Mods/`, including the default `vanilla` pack)
- The generated `serverconfig.txt`

## Sample

See [`samples/gameserver.yaml`](samples/gameserver.yaml) for a deployment manifest example.
