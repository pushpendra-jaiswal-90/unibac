# Sandbox sample data

Synthetic dataset for exercising the LBI pipeline end-to-end without real
NBFC data. All values are generated deterministically from `seed=42`, so
regenerating produces byte-identical files.

> **Never commit real NBFC data to this folder.** It's part of the public repo
> and is covered by a `!sample/**/*.csv` carve-out in `.gitignore`.

## Contents

| Path                                | What it is                                               |
|-------------------------------------|----------------------------------------------------------|
| `manifest.json`                     | Seed, snapshot date, row counts, scenario breakdown.     |
| `sandbox.duckdb`                    | DuckDB file with all four tables — handy for ad-hoc SQL. |
| `csv/loan_snapshot.csv`             | File A — 1,000 loans at `snapshot_date = 2026-10-01`.    |
| `csv/repayments.csv`                | File B — 12 months of EMI history (12,000 rows).         |
| `csv/collection_activity.csv`       | File C — contact attempts for delinquent accounts.       |
| `csv/scenario_tag.csv`              | Ground-truth scenario label per loan (not shipped to the engine). |
| `applicants/APP00{1,2,3}/`          | Raw-format applicant files: `bank_statement.xlsx` (HDFC-style account statement), `cibil_report.pdf` (score + accounts + enquiries), `gstr3b.xlsx` (GSTR-3B summary + GSTR-1 B2B tab). |

## Scenario mix (1,000 borrowers)

| Scenario           | Count | Exercises                                        |
|--------------------|-------|--------------------------------------------------|
| `CURRENT`          | 500   | Happy-path baseline; worklist must *not* pick up.|
| `EARLY_DPD`        | 180   | DPD 1–30, routine follow-up.                     |
| `MID_DPD`          | 100   | DPD 31–60 with recent deterioration.             |
| `LATE_DPD`         |  70   | DPD 61–90 + broken PTP (big score bump).         |
| `NPA`              |  70   | DPD 91+, chronic bouncers, `loan_status = NPA`.  |
| `CHRONIC_BOUNCER`  |  40   | 60% bounce rate; stresses the bounce rule.       |
| `BROKEN_PTP`       |  20   | Fires the broken-promise rule explicitly.        |
| `NO_CONTACT`       |  20   | No activity rows → "no recent contact" bump.     |

## Applicants (CAM builder)

| ID       | Bank         | CIBIL | Expected CAM decision |
|----------|--------------|-------|------------------------|
| `APP001` | Clean, 0 bounces      | 782 | APPROVE               |
| `APP002` | 4 bounces             | 668 | REFER                 |
| `APP003` | 9 bounces, negative EOD | 548 | DECLINE               |

## Regenerate

```bash
cd integrations && pip install -e .
lbi-sandbox-gen --out ../sample
```

## Smoke-test the full CAM pipeline

The raw applicant files feed the Python parsers; the parsed JSON is what the
Rust CAM builder consumes.

```bash
# 1. Parse raw inputs → JSON (via the Python parsers / MCP tools)
python -m unibac_integrations.parsers.bank_statement \
    sample/applicants/APP001/bank_statement.xlsx > /tmp/bank.json
python -m unibac_integrations.parsers.cibil        \
    sample/applicants/APP001/cibil_report.pdf      > /tmp/cibil.json
python -m unibac_integrations.parsers.gst          \
    sample/applicants/APP001/gstr3b.xlsx           > /tmp/gst.json

# 2. Build the CAM
cd core && cargo build --release
./target/release/lbi-core cam \
    --bank  /tmp/bank.json \
    --cibil /tmp/cibil.json \
    --gst   /tmp/gst.json \
    --out   /tmp/cam-app001.json
cat /tmp/cam-app001.json
```
