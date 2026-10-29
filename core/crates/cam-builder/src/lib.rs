//! Credit Appraisal Memo (CAM) builder.
//!
//! Consumes already-parsed artefacts produced by the Python integrations
//! layer (bank-statement, CIBIL, GST JSON files) and emits a structured CAM
//! document that an underwriter can review.

use anyhow::{Context, Result};
use chrono::Utc;
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct BankSummary {
    pub avg_monthly_credit: Decimal,
    pub avg_monthly_debit: Decimal,
    pub bounce_count: u32,
    pub min_eod_balance: Decimal,
}

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct CibilSummary {
    pub score: Option<u16>,
    pub active_accounts: u32,
    pub overdue_amount: Decimal,
    pub enquiries_last_6m: u32,
}

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct GstSummary {
    pub avg_monthly_turnover: Decimal,
    pub filing_regularity_pct: Decimal,
    pub last_filed_period: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Cam {
    pub schema_version: &'static str,
    pub generated_at: String,
    pub bank: BankSummary,
    pub cibil: CibilSummary,
    pub gst: GstSummary,
    pub recommendation: Recommendation,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Recommendation {
    pub decision: String,     // APPROVE / REFER / DECLINE
    pub rationale: Vec<String>,
    pub max_exposure: Decimal,
}

pub fn build(bank: &Path, cibil: &Path, gst: &Path, out: &Path) -> Result<()> {
    tracing::info!(?bank, ?cibil, ?gst, ?out, "cam.build");

    let bank: BankSummary = read_json(bank)?;
    let cibil: CibilSummary = read_json(cibil)?;
    let gst: GstSummary = read_json(gst)?;

    let mut rationale = Vec::new();
    let mut decision = "REFER";

    if let Some(sc) = cibil.score {
        if sc >= 720 { rationale.push(format!("CIBIL {sc} ≥ 720")); decision = "APPROVE"; }
        else if sc < 600 { rationale.push(format!("CIBIL {sc} < 600")); decision = "DECLINE"; }
    } else {
        rationale.push("No CIBIL score available".into());
    }

    if bank.bounce_count > 3 {
        rationale.push(format!("{} bounces in bank statement window", bank.bounce_count));
        decision = "REFER";
    }

    let cam = Cam {
        schema_version: "cam/0.1",
        generated_at: Utc::now().to_rfc3339(),
        bank,
        cibil,
        gst,
        recommendation: Recommendation {
            decision: decision.to_string(),
            rationale,
            max_exposure: Decimal::ZERO,
        },
    };

    std::fs::write(out, serde_json::to_string_pretty(&cam)?)
        .with_context(|| format!("writing {}", out.display()))?;
    Ok(())
}

fn read_json<T: for<'de> Deserialize<'de>>(p: &Path) -> Result<T> {
    let s = std::fs::read_to_string(p).with_context(|| format!("reading {}", p.display()))?;
    Ok(serde_json::from_str(&s)?)
}
