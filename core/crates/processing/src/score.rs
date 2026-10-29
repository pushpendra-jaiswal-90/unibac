use crate::model::{CollectionEvent, LoanSnapshot, Repayment, WorklistItem};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};

/// Weights from the product plan §2 "Illustrative prioritisation score".
/// Must be tuned per NBFC and version-stamped alongside the metric dictionary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreWeights {
    pub current_dpd: u8,
    pub repeated_bounces: u8,
    pub broken_ptp: u8,
    pub overdue_vs_emi: u8,
    pub no_recent_contact: u8,
    pub recent_deterioration: u8,
}

impl Default for ScoreWeights {
    fn default() -> Self {
        Self {
            current_dpd: 30,
            repeated_bounces: 20,
            broken_ptp: 20,
            overdue_vs_emi: 15,
            no_recent_contact: 10,
            recent_deterioration: 5,
        }
    }
}

pub struct PriorityScore;

impl PriorityScore {
    /// Compute a 0–100 explainable score for a single account.
    /// Missing data must stay visible — never silently promote to high risk.
    pub fn compute(
        snap: &LoanSnapshot,
        repayments: &[Repayment],
        events: &[CollectionEvent],
        w: &ScoreWeights,
    ) -> WorklistItem {
        let mut score: u16 = 0;
        let mut reasons = Vec::new();

        let dpd = snap.dpd.unwrap_or(0);
        if dpd >= 90 {
            score += w.current_dpd as u16;
            reasons.push(format!("DPD {dpd} (NPA band)"));
        } else if dpd >= 30 {
            score += (w.current_dpd as u16 * 2) / 3;
            reasons.push(format!("DPD {dpd}"));
        }

        let bounces = repayments.iter().filter(|r| r.payment_status == "BOUNCED").count();
        if bounces >= 2 {
            score += w.repeated_bounces as u16;
            reasons.push(format!("{bounces} bounces in window"));
        }

        let broken_ptp = events.iter().any(|e| e.outcome_code == "PTP_BROKEN");
        if broken_ptp {
            score += w.broken_ptp as u16;
            reasons.push("Broken promise-to-pay".into());
        }

        if snap.emi_amount > Decimal::ZERO && snap.overdue_amount > snap.emi_amount {
            score += w.overdue_vs_emi as u16;
            reasons.push("Overdue exceeds one EMI".into());
        }

        if events.is_empty() {
            score += w.no_recent_contact as u16;
            reasons.push("No recent collection contact".into());
        }

        WorklistItem {
            loan_account_id: snap.loan_account_id.clone(),
            score: score.min(100) as u8,
            reasons,
            overdue_amount: snap.overdue_amount,
            dpd,
            next_action: "CALL".into(),
        }
    }
}
