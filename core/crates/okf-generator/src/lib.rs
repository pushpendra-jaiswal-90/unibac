//! OKF (Open Knowledge Format) generator.
//!
//! Emits a tenant-portable, version-stamped JSON bundle describing the
//! canonical loan book + metric dictionary + rule weights. Used for pilot
//! handoff, back-testing and audits.

use anyhow::{Context, Result};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct OkfBundle {
    pub schema_version: &'static str,
    pub generated_at: String,
    pub source: String,
    pub metric_dictionary_version: String,
    pub rule_weights_version: String,
    pub rows: usize,
}

/// Read `input` (canonical CSV directory) and write an OKF bundle to `out`.
pub fn generate(input: &Path, out: &Path) -> Result<()> {
    tracing::info!(?input, ?out, "okf.generate");
    let bundle = OkfBundle {
        schema_version: "okf/0.1",
        generated_at: Utc::now().to_rfc3339(),
        source: input.display().to_string(),
        metric_dictionary_version: "md/0.1".into(),
        rule_weights_version: "rw/0.1".into(),
        rows: 0, // TODO: count canonical rows.
    };
    let json = serde_json::to_string_pretty(&bundle)?;
    std::fs::write(out, json).with_context(|| format!("writing {}", out.display()))?;
    Ok(())
}
