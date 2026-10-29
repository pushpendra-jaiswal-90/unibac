# Unibac — Loan Book Intelligence

Collections-intelligence platform for Indian vehicle-finance NBFCs. CSV/Excel-first
ingestion of loan snapshots, repayments and collection activity → validated,
explainable, prioritised daily worklists.

See `docs/loan_book_intelligence_initial_product_plan.pdf` (symlinked copy of the
plan) for product context.

## Repo layout

| Path            | Language | Purpose                                                                 |
|-----------------|----------|-------------------------------------------------------------------------|
| `backend/`      | Scala    | HTTP API, orchestration, auth, audit log, serves worklist + dashboard. |
| `core/`         | Rust     | Heavy processing — delinquency engine, OKF generator, CAM builder.     |
| `integrations/` | Python   | Parsers (bank stmt / CIBIL / GST), MCP server, LLM agent.              |
| `shared/`       | —        | Canonical schemas, metric dictionary, sample files.                     |
| `docs/`         | —        | Product plan, architecture notes.                                       |

## Why three languages

- **Scala** — JVM ergonomics for a stateful backend; cats-effect + http4s give a
  typed, concurrent core without a framework. Good fit with the "Scala or Java +
  SQL" guidance in the product plan.
- **Rust** — Deterministic, high-throughput number-crunching for the delinquency
  engine, OKF generator and CAM builder. Called by Scala over a thin FFI /
  sidecar HTTP boundary; by Python via `pyo3` when needed.
- **Python** — Best-in-class parsing ecosystem (`pdfplumber`, `camelot`,
  `openpyxl`), the MCP SDK and the Anthropic/agent SDKs. Natural home for the
  integrations surface.

## Component map

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Scala backend  │───▶│  Rust core      │    │  Python integ.  │
│  (http4s)       │    │  (CLI + lib)    │    │  (MCP + agent)  │
│                 │◀───│  - metrics      │◀───│  - parsers      │
│  REST + audit   │    │  - OKF gen      │    │  - MCP server   │
│                 │    │  - CAM builder  │    │  - LLM agent    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                       │
         └──────── Postgres ────┴───── Object store ────┘
```

## Getting started

Each sub-project has its own README with build + run instructions:
- [`backend/README.md`](backend/README.md)
- [`core/README.md`](core/README.md)
- [`integrations/README.md`](integrations/README.md)
