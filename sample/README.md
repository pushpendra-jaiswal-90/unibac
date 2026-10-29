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
| `applicants/APP00{1,2,3}/`          | Parsed bank / CIBIL / GST JSONs for CAM builder tests.   |

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

## Smoke-test the Rust CAM builder

```bash
cd core && cargo build --release
./target/release/lbi-core cam \
    --bank  ../sample/applicants/APP001/bank.json \
    --cibil ../sample/applicants/APP001/cibil.json \
    --gst   ../sample/applicants/APP001/gst.json \
    --out   /tmp/cam-app001.json
cat /tmp/cam-app001.json
```
