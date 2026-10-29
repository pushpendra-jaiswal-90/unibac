# Canonical schemas

Headers mirrored across Scala (`com.unibac.lbi.domain`), Rust
(`processing::model`) and Python (`unibac_integrations.parsers`). Changing a
header here means updating all three.

| File                         | Entity                                                |
|------------------------------|-------------------------------------------------------|
| `loan_snapshot.csv`         | File A — one row per loan at a stated snapshot date.  |
| `repayments.csv`            | File B — one row per payment / reversal / adjustment. |
| `collection_activity.csv`   | File C — one row per collection attempt or outcome.   |

Metric dictionary and prioritisation-score weights are tracked separately
alongside the OKF bundle version in `docs/metric_dictionary.md` (to be added
during the pilot's week 1–2 "data readiness" phase).
