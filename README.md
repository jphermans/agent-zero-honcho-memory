# Honcho Shared Memory Plugin for Agent Zero

> **Self-hosted, shared persistent memory for Agent Zero through Honcho.**

This plugin connects Agent Zero to a [Honcho](https://honcho.dev) database, enabling durable, searchable memory that can be shared across multiple Agent Zero instances and compatible agents.

## Key Features

- **Persistent Memory** — Store and retrieve meaningful conversation data.
- **Semantic Search** — Honcho's built-in search finds relevant past memories.
- **Single-Agent & Multi-Agent Modes** — Works with one agent or multiple shared agents.
- **Safe by Default** — Secrets redacted, passwords never stored in config, automatic filtering of trivial/secrets content.
- **Granular Privacy Controls** — Choose which message roles to store.

## Requirements

- Agent Zero (tested with current version)
- Honcho server (v2.x / v3.x) running and reachable
- Network access between Agent Zero and the Honcho API

## Installation

### From Plugin Hub (recommended)

1. Open your Agent Zero WebUI.
2. Go to **Plugins** > **Browse** and search for "Honcho Shared Memory".
3. Click **Install**.

### From Git (manual)

```bash
cd /a0/usr/plugins
git clone https://github.com/jphermans/agent-zero-honcho-memory.git honcho_shared_memory
```

Then restart Agent Zero, go to Plugins, and enable the plugin.

## Setup

1. **Configure the Honcho DB password secret**:
   - In Agent Zero, go to **Secrets** and create a secret named `HONCHO_DB_PASSWORD`.
   - Set its value to the API key / password used by your Honcho instance.

2. **Open plugin settings**:
   - In **Plugins**, find "Honcho Shared Memory" and click **Settings**.
   - Fill in:
     - **Honcho Base URL** — e.g., `http://honcho-api:8000` (Docker), `http://192.168.1.100:8000` (LAN), `https://honcho.example.com` (remote).
     - **Workspace ID** — your Honcho workspace name.
     - **Peer ID** — a stable identifier for this peer (e.g., `agent-zero`).
     - **Agent ID** — unique ID for this Agent Zero instance.
   - Click **Test Connection** to verify.
   - Save.

## Memory Model

- **Workspace** → namespace for shared memory.
- **Peer** → identity in a conversation (e.g., "agent-zero", "user").
- **Session** → a conversation thread.
- **Message** → individual stored items with metadata.

By default, only memories explicitly saved via the tools are stored. Enable auto-store in settings if you want automatic capture (with appropriate privacy settings).

## Multi-Agent Configuration

1. Enable **Multi-agent shared memory** in settings.
2. Add the agent IDs of other agents you trust (comma-separated).
3. All listed agents can read each other's memories.

## Security & Privacy

- Passwords are **never** stored in configuration files — they are read from Agent Zero's secret manager.
- TLS verification is **enabled by default**. Disable it only for trusted LAN testing.
- Content that appears to contain secrets (API keys, tokens, passwords) is **automatically filtered** before storage.
- No telemetry, no tracking, no external services. Your data stays on your Honcho server.

## Development

To run tests:
```bash
pytest usr/plugins/honcho_shared_memory/tests/
```

## License

MIT
