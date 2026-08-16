# 🧠 Honcho Shared Memory

> **Shared persistent memory for Agent Zero** through a self-hosted Honcho database.

<p align="center">
  <img src="assets/icon.svg" alt="Honcho Shared Memory icon" width="128" height="128"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.0.7-blue?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/Agent%20Zero-%E2%9C%94%EF%B8%8F%20compatible-4285F4?style=flat-square" alt="Agent Zero compatible"/>
  <img src="https://img.shields.io/badge/python-3.12%2B-purple?style=flat-square" alt="Python 3.12+"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/%F0%9F%A4%96%20compatible-Agent%20Zero-4285F4?style=for-the-badge" alt="Agent Zero"/>
  <img src="https://img.shields.io/badge/%F0%9F%94%97%20compatible-Hermes--Agent-9B59B6?style=for-the-badge" alt="Hermes-Agent"/>
  <img src="https://img.shields.io/badge/%F0%9F%90%BE%20compatible-OpenClaw-F05032?style=for-the-badge" alt="OpenClaw"/>
</p>

---

> **🤖 This plugin was entirely written by the AI assistant Agent Zero (A0).**
> **👥 Contributors:** JPHsystems and Agent Zero

## ✨ Features

| Feature | Description |
|---------|-------------|
| 💾 **Persistent Memory** | Store user preferences, project decisions, and reusable context in Honcho |
| 🔍 **Smart Retrieval** | Automatically search and inject relevant memories before agent responses |
| 🤝 **Multi-Agent** | Share memories across multiple Agent Zero instances or different agents |
| 🕵️ **Secret Redaction** | Automatically detect and redact passwords, tokens, and API keys before storage |
| 🧩 **Compatibility Modes** | Native support for Hermes-Agent and OpenClaw metadata conventions |
| 🔒 **Privacy First** | Auto-storage disabled by default, configurable message type filtering |
| 🎛️ **Clean Settings UI** | Full configuration page with connection testing and diagnostics |

---

## 📊 Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Agent Zero  │     │ Hermes-Agent │     │   OpenClaw   │
│  (instance)  │     │  (instance)  │     │  (instance)  │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │   honcho_memory_   │   get_sessions()   │   getPeerInfo()
       │   store / search    │   createMessage()   │   createChat()
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                    ┌───────▼───────┐
                    │  Honcho API   │
                    │  :8000        │
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │  PostgreSQL   │
                    │  (memory)     │
                    └───────────────┘
```

---

## 🚀 Installation

### From GitHub

```bash
# In Agent Zero, go to Plugins → Install from Git:
https://github.com/jphermans/agent-zero-honcho-memory.git
```

### Manual

```bash
cd /a0/usr/plugins
git clone https://github.com/jphermans/agent-zero-honcho-memory.git honcho_shared_memory
```

Then **restart Agent Zero** to load the plugin.

---

## ⚙️ Setup

### 1. Configure the Secret

Add the **HONCHO_DB_PASSWORD** secret in Agent Zero:

```
Settings → Secrets → Add
Key:   HONCHO_DB_PASSWORD
Value: your-honcho-password
```

> ⚠️ **Never** commit passwords to Git, config files, or logs.

### 2. Configure the Plugin

Open **Settings → Agent → Honcho Shared Memory** and fill in:

| Field | Example | Description |
|-------|---------|-------------|
| **Honcho Base URL** | `http://your-honcho-server:8000` | Full URL to your Honcho API |
| **Connection Mode** | `LAN` | Local, LAN, or Remote |
| **Honcho Workspace ID** | `hermes` | The shared memory namespace |
| **Honcho Peer ID** | `hermes` | Identity within the workspace |
| **Current Agent ID** | `agent-zero-0` | Unique ID for this agent |
| **Agent Compatibility** | `Hermes-Agent` | Match your other agent's format |

### 3. Test Connection

Click **Test Connection** — you should see:

```
✅ Connection successful
  Reachability: ok
  Workspace: hermes
  Peer: ok
  Write: ok
  Read: ok
```

---

## 🤖 Agent Tools

### `honcho_memory_store`

Explicitly store a memory in Honcho:

```json
{
  "content": "User prefers dark mode and Python over JavaScript",
  "memory_type": "preference",
  "tags": ["ui", "language"]
}
```

### `honcho_memory_search`

Search for relevant memories:

```json
{
  "query": "user dark mode preference",
  "limit": 5
}
```

### `honcho_memory_context`

Retrieve a concise context block for model injection — called automatically when auto-retrieval is enabled.

---

## 🔄 Single-Agent vs Multi-Agent

| Mode | Behavior |
|------|----------|
| 🔵 **Single-Agent** | Only this Agent Zero reads/writes memories |
| 🟢 **Multi-Agent** | Multiple agents share the same workspace |

### Multi-Agent Setup

1. Enable **"Multi-agent shared memory"**
2. Add all agent IDs to **"Allowed Agent IDs"** (e.g., `hermes, agent-zero-0`)
3. Enable **"Include shared agent memories"**
4. On the other agent, use the **same workspace and peer**

---

## 🧩 Agent Compatibility

The **Agent Compatibility** dropdown adapts the plugin to different agents' metadata conventions:

| Mode | agent_id in metadata | Field labels |
|------|---------------------|--------------|
| 🟦 **Agent Zero** (default) | ✅ Full metadata | Peer ID / Agent ID |
| 🟣 **Hermes-Agent** | ❌ Minimal metadata | AI Peer / User Peer |
| 🟥 **OpenClaw** | ❌ Minimal metadata | Sender Peer / Owner Peer |

When using Hermes-Agent or OpenClaw mode, **metadata filtering is disabled** so all agents can read each other's stored memories regardless of origin.

---

## 🔐 Security

| Protection | Status |
|-----------|--------|
| Password in secrets only | ✅ `HONCHO_DB_PASSWORD` |
| Secret redaction before storage | ✅ Passwords, tokens, keys, URIs |
| TLS verification | ✅ Enabled by default |
| No hardcoded credentials | ✅ |
| No telemetry / tracking | ✅ |
| No eval / exec | ✅ |

---

## 🧪 Testing

```bash
cd /a0/usr/plugins/honcho_shared_memory
/opt/venv-a0/bin/python -m pytest tests/unit/ -v
```

**Test coverage:**
- Configuration validation (URL, identifiers, int ranges, agent IDs)
- Secret redaction (passwords, tokens, URIs, headers, private keys)
- Compatibility modes (delegated detection, metadata generation)
- 42 unit tests total

---

## 📁 File Structure

```
honcho_shared_memory/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── plugin.yaml
├── default_config.yaml
├── pyproject.toml
├── .gitignore
├── assets/
│   ├── icon.svg
│   ├── icon.png
│   └── icon_128.png
├── backend/
│   ├── client.py          # Honcho SDK wrapper
│   ├── config.py          # Pydantic config model
│   ├── exceptions.py      # Typed plugin exceptions
│   ├── memory.py          # Filtering, metadata, context formatting
│   ├── redaction.py       # Secret detection & redaction
│   └── validation.py      # URL, identifier, agent ID validation
├── api/
│   ├── __init__.py
│   ├── test_connection.py # Connection diagnostics endpoint
│   └── secret_status.py   # Password secret status endpoint
├── tools/
│   ├── honcho_memory_store.py
│   ├── honcho_memory_search.py
│   └── honcho_memory_context.py
├── extensions/
│   └── python/monologue_start/
│       └── _10_honcho_retrieval.py  # Auto-retrieval lifecycle hook
├── webui/
│   └── config.html        # Settings UI
└── tests/
    ├── unit/
    │   ├── test_validation.py
    │   ├── test_redaction.py
    │   └── test_compatibility.py
    └── integration/
```

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **"Empty response from server"** | Restart Agent Zero (clears API handler cache) |
| **"Column agent_id not allowed"** | Set Agent Compatibility to Hermes-Agent or OpenClaw |
| **Settings screen is blank** | Hard-refresh browser (Ctrl+Shift+R) |
| **Connection refused** | Check Honcho is running and URL/port is correct |
| **No memories found** | Verify same workspace + peer as your other agent |

---

## 📄 Requirements

- **Agent Zero** (latest Docker runtime)
- **Honcho** API server (v2.x, tested with Python SDK 2.2.0)
- Python 3.12+

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests (`pytest tests/unit/ -v`)
4. Open a pull request

---

## 📜 License

MIT © 2026

---

<p align="center">
  <sub>Built with ❤️ for the Agent Zero community</sub>
</p>
