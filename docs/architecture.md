# Architecture

```
       ┌────────────┐     HTTP      ┌──────────────┐
NBFC → │  Scala API │──────────────▶│ Rust lbi-core│
upload │  (http4s)  │◀──── JSON ────│ (CLI/sidecar)│
       └─────┬──────┘               └──────┬───────┘
             │                             │
             │                             ▼
             │                      ┌──────────────┐
             │                      │  processing  │
             │                      │  okf-gen     │
             │                      │  cam-builder │
             │                      └──────┬───────┘
             │                             │
             ▼                             │
       ┌────────────┐                      │
       │ Postgres   │                      │
       │ + audit    │                      │
       └────────────┘                      │
                                           │ reads parsed JSON
                                           ▼
                                    ┌──────────────┐
                                    │  Python      │
                                    │  integrations│
                                    │  parsers +   │
                                    │  MCP server +│
                                    │  agent       │
                                    └──────────────┘
```

## Trust boundaries

- Only the Scala backend terminates TLS and enforces tenant isolation.
- Rust core runs as a short-lived subprocess under the backend's uid; it
  never opens its own network sockets in the default deployment.
- Python integrations run in a separate container; the backend talks to the
  MCP server over stdio (via a worker process) or an authenticated HTTP
  endpoint (for agent-triggered flows).

## Data path per upload

1. Scala receives multipart POST, writes raw file to encrypted object store.
2. Row-level validation runs in Rust (streamed); exceptions go to a quarantine
   bucket + the audit log.
3. Canonical rows land in Postgres with `source_file_id` + `ingestion_run_id`.
4. Delinquency engine recomputes DPD, bounce patterns and the priority score;
   results written to the `worklist` + `daily_snapshot` tables.
5. Backend serves the worklist, dashboard and audit APIs.
