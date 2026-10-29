//! Shared domain + delinquency engine.
//!
//! Mirrors the canonical schema in `shared/schemas/`. Keep field names in sync
//! with the Scala `com.unibac.lbi.domain.LoanSnapshot`.

pub mod model;
pub mod score;

pub use model::{CollectionEvent, LoanSnapshot, Repayment, WorklistItem};
pub use score::{PriorityScore, ScoreWeights};
