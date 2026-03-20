# Copilot ACP Agent (Obsidian plugin)

This plugin starts **GitHub Copilot CLI** in **ACP TCP mode** and connects to it as a lightweight ACP client.

It launches:
- `copilot --acp --port 9000`

Then it speaks ACP over TCP using newline-delimited JSON-RPC messages (same framing as ACP stdio NDJSON).

## Requirements
- Obsidian Desktop (Windows x64 supported)
- GitHub Copilot CLI installed and authenticated
- ACP support in Copilot CLI (public preview). See GitHub docs.

## Install
1. Copy this folder into:
   `.obsidian/plugins/copilot-acp-agent/`
2. Ensure the folder contains:
   - `manifest.json`
   - `main.js`
   - `styles.css`
3. Restart Obsidian and enable the plugin under:
   Settings → Community plugins → Installed plugins.

## Usage
- Click the **bot** icon on the left ribbon to open the right-side panel.
- Click **Start + Connect**.
- Type messages and press **Ctrl+Enter** (or click **Send**).
- If Copilot requests permissions (tool calls), a permission card appears with buttons.

## Settings
- Copilot CLI path (default: `copilot`)
- Host and port (default: 127.0.0.1:9000)
- Vault path (passed as `cwd` for `session/new`)

## Notes
- ACP methods used: `initialize`, `session/new`, `session/prompt`, `session/update`, `session/request_permission`, `session/cancel`.
- The ACP major protocol version is 1 in the public schema.
