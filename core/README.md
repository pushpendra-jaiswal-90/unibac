# LBI Core (Rust)

Deterministic, high-throughput processing. Cargo workspace with four crates:

| Crate            | Kind | Purpose                                                       |
|------------------|------|---------------------------------------------------------------|
| `processing`    | lib  | Canonical model + delinquency scoring engine.                 |
| `okf-generator` | lib  | Emits portable OKF (Open Knowledge Format) bundles.           |
| `cam-builder`   | lib  | Builds a Credit Appraisal Memo from bank/CIBIL/GST artefacts. |
| `lbi-core`      | bin  | CLI entry point used by the Scala backend.                    |

## Build

```bash
cd core
cargo build --release
./target/release/lbi-core --help
```

## CLI

```bash
lbi-core worklist   --snapshots s.csv --repayments r.csv --activity a.csv
lbi-core okf        --input ./canonical --out bundle.json
lbi-core cam        --bank bank.json --cibil cibil.json --gst gst.json --out cam.json
```

## Integration contract

- **With Scala backend** — spawned as a short-lived subprocess per request;
  reads canonical CSVs from an object-store path, writes JSON to stdout or a
  path chosen by the backend. Keep the CLI's JSON schema versioned.
- **With Python integrations** — the Python side produces parsed JSON for
  bank/CIBIL/GST; `cam-builder` consumes those JSON blobs.
