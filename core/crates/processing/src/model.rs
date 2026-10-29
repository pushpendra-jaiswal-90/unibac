use chrono::NaiveDate;
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoanSnapshot {
    pub loan_account_id: String,
    pub snapshot_date: NaiveDate,
    pub branch_id: String,
    pub product_type: String,
    pub loan_status: String,
    pub emi_amount: Decimal,
    pub next_due_date: NaiveDate,
    pub overdue_amount: Decimal,
    pub dpd: Option<i32>,
    pub outstanding_principal: Decimal,
    pub collector_id: Option<String>,
    pub loan_start_date: Option<NaiveDate>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Repayment {
    pub loan_account_id: String,
    pub transaction_id: String,
    pub transaction_date: NaiveDate,
    pub amount: Decimal,
    pub transaction_type: String,
    pub payment_status: String,
    pub value_date: Option<NaiveDate>,
    pub payment_channel: Option<String>,
    pub bounce_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollectionEvent {
    pub loan_account_id: String,
    pub activity_date_time: chrono::NaiveDateTime,
    pub collector_id: Option<String>,
    pub activity_type: String,
    pub outcome_code: String,
    pub promise_to_pay_date: Option<NaiveDate>,
    pub promise_to_pay_amount: Option<Decimal>,
    pub actual_payment_amount: Option<Decimal>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorklistItem {
    pub loan_account_id: String,
    pub score: u8,
    pub reasons: Vec<String>,
    pub overdue_amount: Decimal,
    pub dpd: i32,
    pub next_action: String,
}
