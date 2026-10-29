"""Synthetic data generator for sandbox / pilot dry-runs.

Produces canonical CSVs (loan_snapshot / repayments / collection_activity) for
1,000 synthetic vehicle-finance borrowers across 12 months, plus a handful of
applicant files (bank statement, CIBIL, GST) for exercising the CAM builder.

No real NBFC data is ever used here.
"""
