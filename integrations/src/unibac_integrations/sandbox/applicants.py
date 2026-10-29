"""Synthesise applicant source files in realistic formats.

Each applicant gets:

    bank_statement.xlsx   Mimics an Indian retail-bank download:
                          Date | Narration | Chq No | Debit | Credit | Balance.
    cibil_report.pdf      Simplified CIBIL-style report: score, personal info,
                          account summary, enquiry history.
    gstr3b.xlsx           GSTR-3B summary + GSTR-1 outward supplies tabs.

The numbers are driven by `ApplicantProfile` so each profile ends up with a
plausibly APPROVE / REFER / DECLINE CAM outcome.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass
class ApplicantProfile:
    """Numbers that drive all three generated files for one applicant."""

    id: str
    name: str
    pan: str
    gstin: str
    avg_monthly_credit: int
    avg_monthly_debit: int
    opening_balance: int
    bounce_count: int                 # EMI bounces visible in the statement
    cibil_score: int
    active_accounts: int
    overdue_amount: int
    enquiries_last_6m: int
    gst_monthly_turnover: int
    filing_regularity_pct: int        # 0..100


PROFILES: list[ApplicantProfile] = [
    ApplicantProfile(
        id="APP001", name="Ramesh Kumar", pan="ABCPK1234F", gstin="27ABCPK1234F1Z5",
        avg_monthly_credit=850_000, avg_monthly_debit=720_000, opening_balance=125_000,
        bounce_count=0, cibil_score=782, active_accounts=3, overdue_amount=0, enquiries_last_6m=1,
        gst_monthly_turnover=1_200_000, filing_regularity_pct=100,
    ),
    ApplicantProfile(
        id="APP002", name="Sunita Devi", pan="DEFPS5678G", gstin="29DEFPS5678G1Z2",
        avg_monthly_credit=420_000, avg_monthly_debit=395_000, opening_balance=8_000,
        bounce_count=4, cibil_score=668, active_accounts=5, overdue_amount=25_000, enquiries_last_6m=6,
        gst_monthly_turnover=480_000, filing_regularity_pct=75,
    ),
    ApplicantProfile(
        id="APP003", name="Mahesh Yadav", pan="GHIPY9012H", gstin="24GHIPY9012H1Z8",
        avg_monthly_credit=180_000, avg_monthly_debit=195_000, opening_balance=-12_000,
        bounce_count=9, cibil_score=548, active_accounts=7, overdue_amount=85_000, enquiries_last_6m=11,
        gst_monthly_turnover=150_000, filing_regularity_pct=40,
    ),
]


# ---- bank statement -----------------------------------------------------------

_BANK_HEADERS = ["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.",
                 "Deposit Amt.", "Closing Balance"]


def _write_bank_statement(profile: ApplicantProfile, out: Path, rng: random.Random) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Account Statement"

    # Header block (bank name / account holder) — mirrors HDFC/ICICI PDF exports.
    ws["A1"] = "HDFC BANK — ACCOUNT STATEMENT"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:G1")
    ws["A3"] = f"Account Holder: {profile.name}"
    ws["A4"] = f"PAN: {profile.pan}"
    ws["A5"] = "Account No: XXXXXXXX1234    IFSC: HDFC0001234"
    ws["A6"] = "Statement Period: 01-Apr-2026 to 30-Sep-2026"

    header_row = 8
    for col, h in enumerate(_BANK_HEADERS, start=1):
        c = ws.cell(row=header_row, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2E5984")
        c.alignment = Alignment(horizontal="center")

    balance = Decimal(profile.opening_balance)
    row = header_row + 1
    start_day = date(2026, 4, 1)

    # Six months of activity.
    for month_offset in range(6):
        month_start = start_day + timedelta(days=30 * month_offset)
        # Salary / business credit — monthly inflow.
        monthly_credit = Decimal(profile.avg_monthly_credit) * Decimal(rng.uniform(0.85, 1.15))
        balance += monthly_credit
        ws.cell(row=row, column=1, value=(month_start + timedelta(days=1)).strftime("%d/%m/%Y"))
        ws.cell(row=row, column=2, value="NEFT CR-SALARY/BUSINESS INFLOW")
        ws.cell(row=row, column=3, value=f"NEFT{rng.randint(100000, 999999)}")
        ws.cell(row=row, column=4, value=(month_start + timedelta(days=1)).strftime("%d/%m/%Y"))
        ws.cell(row=row, column=5, value=0)
        ws.cell(row=row, column=6, value=float(monthly_credit.quantize(Decimal('0.01'))))
        ws.cell(row=row, column=7, value=float(balance.quantize(Decimal('0.01'))))
        row += 1

        # 8–12 debit transactions per month.
        n_debits = rng.randint(8, 12)
        per_debit = Decimal(profile.avg_monthly_debit) / n_debits
        for i in range(n_debits):
            amt = per_debit * Decimal(rng.uniform(0.6, 1.4))
            balance -= amt
            txn_date = month_start + timedelta(days=rng.randint(2, 28))
            narration = rng.choice([
                "UPI-SWIGGY", "UPI-AMAZON", "ATM WDL", "POS-BIG BAZAAR",
                "EMI-AUTO LOAN", "ELEC BILL AUTOPAY", "INS PREMIUM DEBIT",
            ])
            ws.cell(row=row, column=1, value=txn_date.strftime("%d/%m/%Y"))
            ws.cell(row=row, column=2, value=narration)
            ws.cell(row=row, column=3, value=f"UPI{rng.randint(100000, 999999)}")
            ws.cell(row=row, column=4, value=txn_date.strftime("%d/%m/%Y"))
            ws.cell(row=row, column=5, value=float(amt.quantize(Decimal('0.01'))))
            ws.cell(row=row, column=6, value=0)
            ws.cell(row=row, column=7, value=float(balance.quantize(Decimal('0.01'))))
            row += 1

        # Scheduled EMI bounces.
        bounces_this_month = profile.bounce_count // 6 + (1 if rng.random() < (profile.bounce_count % 6) / 6 else 0)
        for _ in range(bounces_this_month):
            txn_date = month_start + timedelta(days=rng.randint(2, 28))
            ws.cell(row=row, column=1, value=txn_date.strftime("%d/%m/%Y"))
            ws.cell(row=row, column=2, value="ACH DR RETURN - INSUFFICIENT FUNDS")
            ws.cell(row=row, column=3, value=f"ACH{rng.randint(100000, 999999)}")
            ws.cell(row=row, column=4, value=txn_date.strftime("%d/%m/%Y"))
            ws.cell(row=row, column=5, value=0)
            ws.cell(row=row, column=6, value=0)
            ws.cell(row=row, column=7, value=float(balance.quantize(Decimal('0.01'))))
            row += 1

    # Column widths for readability.
    widths = [12, 38, 18, 12, 16, 16, 18]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(ord('A') + i - 1)].width = w

    wb.save(out)


# ---- CIBIL report (PDF) -------------------------------------------------------

def _write_cibil_report(profile: ApplicantProfile, out: Path, rng: random.Random) -> None:
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    story: list = []

    story.append(Paragraph("<b>CIBIL TransUnion — Consumer Credit Information Report</b>", styles["Title"]))
    story.append(Spacer(1, 6 * mm))

    # Score panel.
    score_tbl = Table(
        [["CIBIL SCORE", str(profile.cibil_score)],
         ["Score Range", "300 - 900"],
         ["Report Date", "2026-09-30"]],
        colWidths=[60 * mm, 40 * mm],
    )
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR",  (0, 0), (0, -1), colors.whitesmoke),
        ("FONTNAME",   (1, 0), (1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (1, 0), (1, 0), 20),
        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 8 * mm))

    # Personal information.
    story.append(Paragraph("<b>Personal Information</b>", styles["Heading2"]))
    pi = Table([
        ["Name",         profile.name],
        ["PAN",          profile.pan],
        ["Date of Birth","1985-03-14"],
        ["Gender",       "Male"],
        ["Address",      "12, MG Road, Pune, Maharashtra 411001"],
    ], colWidths=[40 * mm, 120 * mm])
    pi.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1f5"))]))
    story.append(pi)
    story.append(Spacer(1, 6 * mm))

    # Account summary.
    story.append(Paragraph("<b>Account Information</b>", styles["Heading2"]))
    acc_rows = [["Lender", "Account Type", "Opened", "Sanctioned", "Current Balance", "Overdue", "DPD (6m)"]]
    rem_overdue = profile.overdue_amount
    for i in range(profile.active_accounts):
        od = rem_overdue if i == profile.active_accounts - 1 else rng.randint(0, max(rem_overdue, 1) // max(profile.active_accounts - i, 1))
        rem_overdue = max(0, rem_overdue - od)
        acc_rows.append([
            rng.choice(["HDFC Bank", "ICICI Bank", "SBI", "Bajaj Finance", "Axis Bank"]),
            rng.choice(["Auto Loan", "Credit Card", "Personal Loan", "Home Loan"]),
            f"202{rng.randint(0, 5)}-0{rng.randint(1,9)}",
            f"{rng.randint(50, 800) * 1000:,}",
            f"{rng.randint(10, 500) * 1000:,}",
            f"{od:,}",
            "0" if od == 0 else f"{rng.randint(30, 150)}",
        ])
    acc = Table(acc_rows, colWidths=[28*mm, 26*mm, 20*mm, 24*mm, 28*mm, 20*mm, 18*mm])
    acc.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
    ]))
    story.append(acc)
    story.append(Spacer(1, 6 * mm))

    # Enquiries.
    story.append(Paragraph("<b>Enquiry Information (last 6 months)</b>", styles["Heading2"]))
    enq_rows = [["Date", "Enquiring Member", "Purpose", "Amount"]]
    for _ in range(profile.enquiries_last_6m):
        enq_rows.append([
            f"2026-0{rng.randint(4,9)}-{rng.randint(1,28):02d}",
            rng.choice(["Bajaj Finance", "Chola MS", "Sundaram Finance", "Shriram City"]),
            rng.choice(["Auto Loan", "CV Loan", "Personal Loan"]),
            f"{rng.randint(100, 1500) * 1000:,}",
        ])
    enq = Table(enq_rows, colWidths=[28*mm, 50*mm, 40*mm, 30*mm])
    enq.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
    ]))
    story.append(enq)

    doc.build(story)


# ---- GST — GSTR-3B + GSTR-1 workbook -----------------------------------------

def _write_gst_xlsx(profile: ApplicantProfile, out: Path, rng: random.Random) -> None:
    wb = Workbook()

    # GSTR-3B summary (six months).
    ws3b = wb.active
    ws3b.title = "GSTR-3B Summary"
    hdr = ["Return Period", "GSTIN", "Filed On",
           "Outward Taxable Supplies", "IGST", "CGST", "SGST", "Total Tax Paid"]
    for col, h in enumerate(hdr, start=1):
        c = ws3b.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1f4e79")

    row = 2
    for month_offset in range(6):
        period_dt = date(2026, 4, 1) + timedelta(days=30 * month_offset)
        filed = rng.random() * 100 < profile.filing_regularity_pct
        turnover = Decimal(profile.gst_monthly_turnover) * Decimal(rng.uniform(0.8, 1.2))
        igst = turnover * Decimal("0.09")
        cgst = turnover * Decimal("0.09")
        sgst = turnover * Decimal("0.00")  # intra-state simplification
        ws3b.cell(row=row, column=1, value=period_dt.strftime("%m-%Y"))
        ws3b.cell(row=row, column=2, value=profile.gstin)
        ws3b.cell(row=row, column=3, value=(period_dt + timedelta(days=20)).strftime("%Y-%m-%d") if filed else "NOT FILED")
        ws3b.cell(row=row, column=4, value=float(turnover.quantize(Decimal('0.01'))))
        ws3b.cell(row=row, column=5, value=float(igst.quantize(Decimal('0.01'))))
        ws3b.cell(row=row, column=6, value=float(cgst.quantize(Decimal('0.01'))))
        ws3b.cell(row=row, column=7, value=float(sgst.quantize(Decimal('0.01'))))
        ws3b.cell(row=row, column=8, value=float((igst + cgst + sgst).quantize(Decimal('0.01'))))
        row += 1

    for col, w in enumerate([16, 20, 14, 24, 14, 14, 14, 18], start=1):
        ws3b.column_dimensions[chr(ord('A') + col - 1)].width = w

    # GSTR-1 outward supplies (abbreviated B2B list).
    ws1 = wb.create_sheet("GSTR-1 B2B")
    hdr1 = ["Invoice No", "Invoice Date", "Recipient GSTIN", "Taxable Value", "IGST", "CGST", "SGST"]
    for col, h in enumerate(hdr1, start=1):
        c = ws1.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1f4e79")

    for i in range(1, 25):
        inv_date = date(2026, 9, 1) + timedelta(days=rng.randint(0, 29))
        val = Decimal(profile.gst_monthly_turnover) / Decimal(25) * Decimal(rng.uniform(0.5, 1.5))
        ws1.cell(row=i + 1, column=1, value=f"INV/2026/{1000 + i}")
        ws1.cell(row=i + 1, column=2, value=inv_date.strftime("%Y-%m-%d"))
        ws1.cell(row=i + 1, column=3, value=f"{rng.randint(10,37):02d}{profile.pan[:5]}XXXX{rng.randint(1000,9999)}1Z1")
        ws1.cell(row=i + 1, column=4, value=float(val.quantize(Decimal('0.01'))))
        ws1.cell(row=i + 1, column=5, value=float((val * Decimal("0.09")).quantize(Decimal('0.01'))))
        ws1.cell(row=i + 1, column=6, value=float((val * Decimal("0.09")).quantize(Decimal('0.01'))))
        ws1.cell(row=i + 1, column=7, value=0.0)

    for col, w in enumerate([18, 14, 24, 16, 14, 14, 14], start=1):
        ws1.column_dimensions[chr(ord('A') + col - 1)].width = w

    wb.save(out)


# ---- entry point --------------------------------------------------------------

def write_applicants(out_root: Path, rng: random.Random | None = None) -> list[str]:
    """Emit raw-format artefacts for every profile. Returns the applicant IDs."""
    rng = rng or random.Random(42)
    written: list[str] = []
    for profile in PROFILES:
        d = out_root / "applicants" / profile.id
        d.mkdir(parents=True, exist_ok=True)
        _write_bank_statement(profile, d / "bank_statement.xlsx", rng)
        _write_cibil_report  (profile, d / "cibil_report.pdf",    rng)
        _write_gst_xlsx      (profile, d / "gstr3b.xlsx",         rng)
        written.append(profile.id)
    return written
