# LBI Integrations (Python)

Parsing + agent surface. Three concerns live here:

1. **Parsers** — bank statements, CIBIL reports, GST returns →
   canonical JSON summaries consumed by `core/crates/cam-builder`.
2. **MCP server** (`lbi-mcp`) — exposes the parsers + a thin wrapper
   over the Rust `lbi-core` CLI as MCP tools, so an MCP-capable client
   (Claude, Claude Code, …) can drive the pipeline.
3. **Agent** (`lbi-agent`) — Claude-powered underwriting loop that uses the
   MCP tools to produce a Credit Appraisal Memo + recommendation.

## Install

```bash
cd integrations
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
# MCP server (stdio transport — launched by an MCP client)
lbi-mcp

# Agent on one applicant directory
export ANTHROPIC_API_KEY=…
lbi-agent /path/to/applicant_dir
```

## Layout

```
src/unibac_integrations/
├── parsers/         # bank_statement / cibil / gst
├── mcp_server/      # FastMCP server exposing parsers + core CLI
└── agent/           # Anthropic agent entry point
```
