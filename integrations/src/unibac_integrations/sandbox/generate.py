"""Generate the sandbox dataset (CSVs + applicant JSONs) deterministically.

Uses DuckDB as the staging engine: data is built in Python, loaded into an
on-disk `sandbox.db`, then exported to the canonical CSVs. The DB file is
useful on its own for ad-hoc SQL exploration during pilot dry-runs.

Usage:
    lbi-sandbox-gen --out sample/
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb

from .applicants import PROFILES, write_applicants
from .scenarios import BRANCHES, COLLECTORS, PRODUCTS, SCENARIOS, Scenario

SEED = 42
SNAPSHOT_DATE = date(2026, 10, 1)
HISTORY_MONTHS = 12


@dataclass
class Loan:
    loan_account_id: str
    scenario: str
    snapshot_date: date
    branch_id: str
    product_type: str
    loan_status: str
    emi_amount: Decimal
    next_due_date: date
    overdue_amount: Decimal
    dpd: int
    outstanding_principal: Decimal
    collector_id: str
    loan_start_date: date


def _emi_for_product(product: str, rng: random.Random) -> Decimal:
    base = {
        "LCV":     (15000, 35000),
        "MCV":     (25000, 55000),
        "HCV":     (40000, 95000),
        "TRUCK":   (35000, 80000),
        "BUS":     (30000, 70000),
        "USED_CV": (12000, 28000),
    }[product]
    return Decimal(rng.randint(*base))


def _generate_loans(rng: random.Random) -> list[Loan]:
    loans: list[Loan] = []
    idx = 0
    for scenario in SCENARIOS:
        for _ in range(scenario.weight):
            idx += 1
            product = rng.choice(PRODUCTS)
            emi = _emi_for_product(product, rng)
            dpd = rng.randint(*scenario.dpd_range)
            tenure_months = rng.randint(24, 60)
            principal = emi * tenure_months * Decimal("0.6")
            start = SNAPSHOT_DATE - timedelta(days=rng.randint(90, 1500))
            overdue = emi * (1 + dpd // 30) if dpd > 0 else Decimal(0)
            loans.append(
                Loan(
                    loan_account_id=f"LN{idx:06d}",
                    scenario=scenario.code,
                    snapshot_date=SNAPSHOT_DATE,
                    branch_id=rng.choice(BRANCHES),
                    product_type=product,
                    loan_status="NPA" if scenario.code == "NPA" else "ACTIVE",
                    emi_amount=emi,
                    next_due_date=SNAPSHOT_DATE + timedelta(days=rng.randint(1, 30)),
                    overdue_amount=overdue.quantize(Decimal("1")),
                    dpd=dpd,
                    outstanding_principal=principal.quantize(Decimal("1")),
                    collector_id=rng.choice(COLLECTORS),
                    loan_start_date=start,
                )
            )
    return loans


def _generate_repayments(loans: list[Loan], scenario_map: dict[str, Scenario], rng: random.Random):
    rows = []
    txn_id = 0
    for loan in loans:
        scenario = scenario_map[loan.scenario]
        # Walk back HISTORY_MONTHS from snapshot, one EMI due per month.
        for m in range(HISTORY_MONTHS):
            due = SNAPSHOT_DATE - timedelta(days=30 * m)
            bounced = rng.random() < scenario.bounce_rate
            status = "BOUNCED" if bounced else "SUCCESS"
            txn_id += 1
            rows.append({
                "loan_account_id":  loan.loan_account_id,
                "transaction_id":   f"TX{txn_id:08d}",
                "transaction_date": due,
                "amount":           float(loan.emi_amount),
                "transaction_type": "EMI",
                "payment_status":   status,
                "value_date":       due,
                "payment_channel":  rng.choice(["NACH", "UPI", "CASH", "CHEQUE"]),
                "bounce_reason":    rng.choice(["INSUFFICIENT_FUNDS", "ACCOUNT_FROZEN"]) if bounced else None,
            })
    return rows


def _generate_activity(loans: list[Loan], scenario_map: dict[str, Scenario], rng: random.Random):
    rows = []
    for loan in loans:
        scenario = scenario_map[loan.scenario]
        if not scenario.recent_contact and not scenario.broken_ptp:
            continue
        # One contact event per week over the last 4 weeks for engaged accounts.
        weeks = 4 if scenario.recent_contact else 1
        for w in range(weeks):
            when = datetime.combine(SNAPSHOT_DATE, datetime.min.time()) - timedelta(days=7 * w, hours=rng.randint(0, 23))
            if scenario.broken_ptp and w == 0:
                outcome = "PTP_BROKEN"
                ptp_date = SNAPSHOT_DATE - timedelta(days=rng.randint(1, 7))
                ptp_amt = float(loan.emi_amount)
            else:
                outcome = rng.choice(["CONTACTED", "NO_ANSWER", "PTP_MADE"])
                ptp_date = SNAPSHOT_DATE + timedelta(days=rng.randint(1, 14)) if outcome == "PTP_MADE" else None
                ptp_amt = float(loan.emi_amount) if outcome == "PTP_MADE" else None
            rows.append({
                "loan_account_id":       loan.loan_account_id,
                "activity_date_time":    when,
                "collector_id":          loan.collector_id,
                "activity_type":         rng.choice(["CALL", "VISIT", "SMS"]),
                "outcome_code":          outcome,
                "promise_to_pay_date":   ptp_date,
                "promise_to_pay_amount": ptp_amt,
                "actual_payment_amount": None,
                "next_action_date":      SNAPSHOT_DATE + timedelta(days=rng.randint(1, 10)),
                "escalation_status":     "FIELD" if loan.dpd > 60 else "TELE",
            })
    return rows


# ---- Main entry point ---------------------------------------------------------


def generate(out: Path) -> None:
    rng = random.Random(SEED)
    scenario_map = {s.code: s for s in SCENARIOS}

    loans      = _generate_loans(rng)
    repayments = _generate_repayments(loans, scenario_map, rng)
    activity   = _generate_activity(loans, scenario_map, rng)

    csv_dir = out / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    db_path = out / "sandbox.duckdb"
    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE loan_snapshot (
            loan_account_id       VARCHAR,
            snapshot_date         DATE,
            branch_id             VARCHAR,
            product_type          VARCHAR,
            loan_status           VARCHAR,
            emi_amount            DECIMAL(14,2),
            next_due_date         DATE,
            overdue_amount        DECIMAL(14,2),
            dpd                   INTEGER,
            outstanding_principal DECIMAL(14,2),
            collector_id          VARCHAR,
            loan_start_date       DATE
        );
        CREATE TABLE scenario_tag (loan_account_id VARCHAR, scenario VARCHAR);
        CREATE TABLE repayments (
            loan_account_id   VARCHAR,
            transaction_id    VARCHAR,
            transaction_date  DATE,
            amount            DECIMAL(14,2),
            transaction_type  VARCHAR,
            payment_status    VARCHAR,
            value_date        DATE,
            payment_channel   VARCHAR,
            bounce_reason     VARCHAR
        );
        CREATE TABLE collection_activity (
            loan_account_id       VARCHAR,
            activity_date_time    TIMESTAMP,
            collector_id          VARCHAR,
            activity_type         VARCHAR,
            outcome_code          VARCHAR,
            promise_to_pay_date   DATE,
            promise_to_pay_amount DECIMAL(14,2),
            actual_payment_amount DECIMAL(14,2),
            next_action_date      DATE,
            escalation_status     VARCHAR
        );
    """)

    con.executemany(
        "INSERT INTO loan_snapshot VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [(l.loan_account_id, l.snapshot_date, l.branch_id, l.product_type, l.loan_status,
          l.emi_amount, l.next_due_date, l.overdue_amount, l.dpd, l.outstanding_principal,
          l.collector_id, l.loan_start_date) for l in loans],
    )
    con.executemany(
        "INSERT INTO scenario_tag VALUES (?,?)",
        [(l.loan_account_id, l.scenario) for l in loans],
    )
    con.executemany(
        "INSERT INTO repayments VALUES (?,?,?,?,?,?,?,?,?)",
        [(r["loan_account_id"], r["transaction_id"], r["transaction_date"], r["amount"],
          r["transaction_type"], r["payment_status"], r["value_date"], r["payment_channel"],
          r["bounce_reason"]) for r in repayments],
    )
    con.executemany(
        "INSERT INTO collection_activity VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(a["loan_account_id"], a["activity_date_time"], a["collector_id"], a["activity_type"],
          a["outcome_code"], a["promise_to_pay_date"], a["promise_to_pay_amount"],
          a["actual_payment_amount"], a["next_action_date"], a["escalation_status"]) for a in activity],
    )

    con.execute(f"COPY loan_snapshot        TO '{csv_dir / 'loan_snapshot.csv'}'        (HEADER, DELIMITER ',')")
    con.execute(f"COPY repayments           TO '{csv_dir / 'repayments.csv'}'           (HEADER, DELIMITER ',')")
    con.execute(f"COPY collection_activity  TO '{csv_dir / 'collection_activity.csv'}'  (HEADER, DELIMITER ',')")
    con.execute(f"COPY scenario_tag         TO '{csv_dir / 'scenario_tag.csv'}'         (HEADER, DELIMITER ',')")

    summary = con.execute("""
        SELECT scenario, COUNT(*) AS n
        FROM scenario_tag
        GROUP BY scenario
        ORDER BY n DESC
    """).fetchall()

    con.close()

    applicant_ids = write_applicants(out, rng)

    manifest = {
        "generated_at":  datetime.now().isoformat(timespec="seconds"),
        "seed":          SEED,
        "snapshot_date": SNAPSHOT_DATE.isoformat(),
        "loans":         len(loans),
        "repayments":    len(repayments),
        "activity":      len(activity),
        "scenarios":     [{"code": code, "count": n} for code, n in summary],
        "applicants":    applicant_ids,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"✓ wrote {len(loans)} loans / {len(repayments)} repayments / {len(activity)} activity rows")
    print(f"✓ sandbox DB: {db_path}")
    print(f"✓ CSVs:       {csv_dir}")
    print(f"✓ applicants: {out / 'applicants'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the Unibac LBI sandbox dataset.")
    ap.add_argument("--out", type=Path, default=Path("sample"), help="Output directory (default: sample/).")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    generate(args.out)


if __name__ == "__main__":
    main()
