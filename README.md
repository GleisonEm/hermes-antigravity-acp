# Hermes Antigravity ACP provider

Google Antigravity (official ACP kernel) as a first-class Hermes provider:
`antigravity-acp` — same architecture as the built-in `copilot-acp`, with
real kernel model switching (`gemini-3.7-flash-high|medium|low`, 3.6 family,
pro variants) via `session/set_config_option`.

```
Hermes ── ACP (stdio JSON-RPC) ── agy_acp_server.par ── Google Antigravity
```

## Install (one line)

```bash
curl -fsSL https://raw.githubusercontent.com/GleisonEm/hermes-antigravity-acp/main/install.sh | bash
```

Requirements:

- Hermes Agent **installed from git** (`~/.hermes/hermes-agent`, v0.20.0+).
  Pip/standalone installs cannot be patched this way.
- The **Antigravity ACP kernel** (`agy_acp_server.par`). macOS: the Zed
  "Antigravity" extension downloads it into
  `~/Library/Application Support/Zed/external_agents/registry/antigravity-acp/`.
  Other platforms: `export HERMES_ANTIGRAVITY_ACP_COMMAND=/path/to/agy_acp_server.par`.
- Your **own** Antigravity login (oauth-personal) — the kernel authenticates
  once via Zed or the AGY CLI.

## Use

```bash
hermes chat -q "review this plan" --provider antigravity-acp -m gemini-3.7-flash-high
hermes config set model.provider antigravity-acp          # default for profile
hermes config set model.default gemini-3.7-flash-medium
```

Models (kernel listing): `gemini-3.7-flash-high|medium|low`,
`gemini-3.6-flash-high|medium|low`, `gemini-3-flash-agent`,
`gemini-3.5-flash-low|extra-low`, `gemini-pro-agent`, `gemini-3.1-pro-low`,
plus `antigravity-acp` (= kernel default). Switching is real: the client
sends `session/set_config_option {configId: "model", value: <slug>}` (note:
`configId`, NOT `configOption`).

## What it changes

| Layer | Files |
|---|---|
| Core Hermes (git checkout) | 16 files patch — provider registration, runtime dispatch, ACP client model-switch support, `/model` picker, setup flow, dashboard, delegation, mid-session switch/fallback fixes |
| User plugin (outside repo) | `model-providers/antigravity-acp/` → `$HERMES_HOME/plugins/model-providers/` (ProviderProfile) |
| Environment (machine) | kernel binary + OAuth + optional symlink — NOT part of the patch |

After any `hermes update` (or git pull), **re-run apply.sh** — idempotent:

```bash
~/.hermes/scripts/antigravity-acp/apply.sh
```

If the patch no longer applies on a newer Hermes: `git apply --3way` or follow
`README.md` (pitfalls section) — the provider is wired in the same ~16 spots
the upstream `copilot-acp` uses; adding a NEW ACP provider means repeating
them upstream-side too.

## Known limitations (by design)

- Kernel reasoning (thinking) is NOT streamed (`agent_thought_chunk` never
  fires; no config knob) — Google does not expose chain-of-thought.
- The ACP client denies kernel permission requests → the kernel is a
  **consulting brain**, not a file-writer. For code campaigns use the agy CLI
  headless (`agy -p --mode=accept-edits`).
- No images through the ACP text channel.
- Per-request kernel process (no cross-turn state inside the kernel).

## License

MIT — see LICENSE.