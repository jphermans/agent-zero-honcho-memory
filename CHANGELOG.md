# Changelog

## [0.0.7] - 2026-08-16

### Fixed
- Fixed write/read test-message actions that failed with `Session a0-plugin-test not found` after the first cleanup by using a unique timestamped test session ID for every write and selecting/deleting only the newest dedicated test session; production and Hermes Agent sessions are never touched.
- Updated plugin version to 0.0.7.

## [0.0.6] - 2026-08-16

### Added
- Settings-page `Write Test Message` and `Read Test Message` actions.
- `write_test_message` API handler: writes a timestamped `Honcho test from A0` marker to the dedicated `a0-plugin-test` session.
- `read_test_message` API handler: retrieves the newest test marker and cleans up the dedicated test session.
- `backend/test_message.py` helpers for deterministic test content, detection, and latest-message extraction.

### Changed
- Updated plugin version to 0.0.6.

## [0.0.5] - 2026-08-15

### Added
- Loopback-only `reload_backend` API endpoint to refresh plugin backend modules in-place without restarting Agent Zero.

## [0.0.4] - 2026-08-15

### Added
- Automatic shared-memory storage (`auto_store`) through a new `monologue_end` lifecycle extension.
- Transparent SSH local-forward fallback when the configured Honcho host is not directly routable.
- Plugin-level `hooks.py` that normalizes effective configuration and resolves secret aliases at runtime.

### Fixed
- Explicit `honcho_memory_store` requests were incorrectly rejected because role-based privacy flags were applied to manual storage.
- `allowed_agent_ids` could remain empty while `allowed_agent_ids_string` was populated in multi-agent mode.
- Honcho filter rejection now fallback-retries without filters for message retrieval as well as search.

## [0.0.3] - 2026-07-21

### Changed
- New plugin icon: database cylinder with three connected agent nodes (SVG + PNG 512px + PNG 128px).
- Rewritten README.md with colorful shields.io badges, emoji sections, and architecture diagram.
- Added Hermes-Agent and OpenClaw compatibility badges to README.
- Added troubleshooting table to README.

## [0.0.2] - 2026-07-21

### Fixed
- Fixed import error in `backend/client.py` (private module `honcho._client` → public `honcho` package).
- Removed stray `.toggle-0` file preventing plugin activation on startup.
- Fixed `config.html` settings page rendering: removed broken external JS imports causing `SyntaxError`.
- Fixed API handlers: changed from `def get()`/`def post()` to mandatory `async def process(self, input, request)`.
- Separated `SecretStatusHandler` into its own file (`api/secret_status.py`) with `get_methods` returning `["GET"]`.
- Made `search_messages()` resilient: automatically retries without filters when Honcho rejects unknown filter columns (e.g., `agent_id` from Hermes/OpenClaw messages).
- Added `api/__init__.py` for proper package discovery.

### Added
- Agent compatibility dropdown (Agent Zero, Hermes-Agent, OpenClaw) with dynamic field labels.
- `_is_delegated_mode()` helper and `compatibility` parameter in `generate_metadata()`.
- `skip_metadata` and `skip_filters` parameters to `HonchoClient` methods.
- 9 unit tests for compatibility modes (42 tests total).
- Null-check error handling in `testConnection()` JavaScript function.

## [0.0.1] - 2026-07-21

### Added
- Initial release of Honcho Shared Memory plugin.
- Three agent tools: `honcho_memory_store`, `honcho_memory_search`, `honcho_memory_context`.
- Lifecycle hook extension for automatic memory retrieval before agent response.
- Settings UI with full configuration for Honcho connection, workspace, peer, agent identity, and automation flags.
- API handlers for connection testing and secret status check.
- Multi-agent shared memory mode with allowed agent ID filtering.
- Secret-redaction utilities and memory content filtering.
- Comprehensive unit tests for validation and redaction.
- Proper icon assets (SVG + PNG).
