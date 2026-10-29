"""Scenario definitions for the synthetic loan book.

Each scenario describes a cohort of borrowers whose behaviour exercises one
or more rules in the delinquency engine. Weights determine the cohort size
across the 1,000-borrower sample.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    code: str
    weight: int                # relative share of the 1,000 borrowers
    dpd_range: tuple[int, int] # min, max days-past-due at snapshot
    bounce_rate: float         # probability each EMI bounces
    broken_ptp: bool
    recent_contact: bool
    deteriorating: bool
    description: str


SCENARIOS: list[Scenario] = [
    Scenario("CURRENT",         500, (0, 0),      0.00, False, True,  False,
             "Performing accounts, no overdue, routine contact."),
    Scenario("EARLY_DPD",       180, (1, 30),     0.05, False, True,  False,
             "First-bucket delinquency, usually curable."),
    Scenario("MID_DPD",         100, (31, 60),    0.15, False, True,  True,
             "Second-bucket deterioration, needs active follow-up."),
    Scenario("LATE_DPD",         70, (61, 90),    0.25, True,  False, True,
             "Approaching NPA; recent broken promise-to-pay."),
    Scenario("NPA",              70, (91, 240),   0.40, True,  False, False,
             "Classified NPA, chronic non-payment."),
    Scenario("CHRONIC_BOUNCER",  40, (15, 75),    0.60, False, True,  True,
             "Repeated bounces across multiple EMIs."),
    Scenario("BROKEN_PTP",       20, (10, 45),    0.10, True,  True,  False,
             "Promised to pay, missed the committed date."),
    Scenario("NO_CONTACT",       20, (20, 60),    0.20, False, False, True,
             "No successful collector contact in the window."),
]

assert sum(s.weight for s in SCENARIOS) == 1000, "scenario weights must sum to 1000"


BRANCHES   = [f"BR{i:03d}" for i in range(1, 11)]           # 10 branches
PRODUCTS   = ["LCV", "MCV", "HCV", "TRUCK", "BUS", "USED_CV"]
COLLECTORS = [f"COL{i:03d}" for i in range(1, 26)]          # 25 collectors
