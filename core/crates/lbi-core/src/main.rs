use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::PathBuf;

/// Unibac Loan-Book Intelligence core CLI.
///
/// Called out from the Scala backend; also usable standalone for one-off runs.
#[derive(Parser, Debug)]
#[command(name = "lbi-core", version, about)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand, Debug)]
enum Cmd {
    /// Build a prioritised worklist from the canonical CSVs.
    Worklist {
        #[arg(long)] snapshots: PathBuf,
        #[arg(long)] repayments: PathBuf,
        #[arg(long)] activity: PathBuf,
        #[arg(long, default_value_t = 100)] limit: usize,
    },
    /// Produce an OKF (Open Credit Facilitator / open-knowledge format) bundle.
    Okf {
        #[arg(long)] input: PathBuf,
        #[arg(long)] out: PathBuf,
    },
    /// Build a CAM (Credit Appraisal Memo) from processed artefacts.
    Cam {
        #[arg(long)] bank: PathBuf,
        #[arg(long)] cibil: PathBuf,
        #[arg(long)] gst: PathBuf,
        #[arg(long)] out: PathBuf,
    },
}

fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Worklist { snapshots, repayments, activity, limit } => {
            tracing::info!(?snapshots, ?repayments, ?activity, limit, "worklist");
            // TODO: load CSVs via `csv` crate and call processing::PriorityScore.
            println!("[]");
        }
        Cmd::Okf { input, out } => {
            okf_generator::generate(&input, &out)?;
        }
        Cmd::Cam { bank, cibil, gst, out } => {
            cam_builder::build(&bank, &cibil, &gst, &out)?;
        }
    }
    Ok(())
}
