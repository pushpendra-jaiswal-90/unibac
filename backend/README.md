# LBI Backend (Scala)

HTTP API + orchestration layer. Written in Scala 3, http4s + cats-effect,
doobie for Postgres.

## Responsibilities

- Multi-tenant file intake endpoint (`POST /v1/ingest/{loan_snapshot|repayments|collection_activity}`).
- Delegates heavy processing to the Rust `lbi-core` sidecar.
- Serves worklist, dashboard and audit endpoints.
- Owns authn/authz, tenant isolation and the audit log.

## Build & run

```bash
cd backend
sbt compile
sbt run
# server on :8080 — try `curl :8080/healthz`
```

## Endpoints (v1 skeleton)

| Method | Path                                     | Purpose                              |
|--------|------------------------------------------|--------------------------------------|
| GET    | `/healthz`                               | Liveness                             |
| POST   | `/v1/ingest/{kind}?tenant=…`             | Upload CSV/XLSX                      |
| GET    | `/v1/worklist?tenant=…&branch=…`         | Prioritised daily worklist           |
| GET    | `/v1/dashboard?tenant=…`                 | Collection efficiency / cure / roll  |
| GET    | `/v1/audit?limit=…`                      | Audit trail                          |

All request handlers are currently stubs — wire them to the Rust core and
Postgres as the first implementation milestone.

## Layout

```
src/main/scala/com/unibac/lbi/
├── Main.scala           # Ember server bootstrap
├── api/Routes.scala     # http4s routes
├── domain/Model.scala   # Tenant/Loan/Worklist opaque types + case classes
├── ingestion/           # File intake service (stub)
├── metrics/             # Delegates to Rust core (stub)
└── audit/               # In-memory audit log (replace with Postgres)
```
