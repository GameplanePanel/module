# Gameplane modules

OCI game templates for Gameplane. Each `<name>/` folder holds `module.yaml`,
`template.yaml`, `README.md` and optional `icon.png`, `specs.md`, `samples/`.
`build.sh push` publishes them; `validate.py` preflight-checks them in CI.

## Translations

A module can ship translations in `<name>/locales/<tag>.json` (flat JSON,
message id to ICU message).

- `locales/en.json` is the English reference. It is generated, never
  hand-written: `gp-module i18n extract <name>`. It is not pushed to the registry.
- To add a language, copy `en.json` to `locales/<tag>.json` (a valid language
  tag such as `de` or `pt-BR`), translate the values, keep the placeholders,
  then run `gp-module i18n stamp <name>` to record the source hashes.
- `build.sh push` adds one layer per `locales/<tag>.json` (except `en.json`).
- CI runs `i18n-check --module` on every module with a `locales/` folder: ids
  must match the template, placeholders must match English, and `en.json`
  must not drift from the template.
