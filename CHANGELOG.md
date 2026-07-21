# Changelog

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
