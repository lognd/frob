//! `init [--preset P] [--force]`: scaffold a starter `crunk.toml`, bucket dirs, reset and tokens.
//!
//! The scaffold is validated as a spec before anything is written, so a failure leaves the
//! directory untouched, and a successful one passes `crunk check`.

// frob:ticket 01M43ATD7ZGTNCY5036AYEJR7P

pub mod detect;
pub mod scaffold;

use gob_cli::clap::{ArgMatches, builder::PossibleValuesParser};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

/// Scaffold a crunk project in the working directory.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "init",
    product = "crunk",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct Init {
    preset: String,
    force: bool,
}

/// `Init` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct InitArgs {
    #[arg(
        long,
        value_name = "PRESET",
        default_value = "default",
        value_parser = PossibleValuesParser::new(crunk_spec::presets::preset_names()),
        help = "Starter design spec to write"
    )]
    preset: String,
    #[arg(long, help = "Overwrite an existing crunk.toml and reset.css")]
    force: bool,
}

/// Output of `init`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct InitData {
    /// The preset written.
    pub preset: String,
    /// Sections appended from project detection (`jsx`, `tailwind`).
    pub detected: Vec<String>,
    /// Every path written, relative to the project root, sorted.
    pub written: Vec<String>,
}

impl Command for Init {
    type Data = InitData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<InitArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<InitArgs>(m)?;
        Ok(Self {
            preset: a.preset,
            force: a.force,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<InitData> {
        let data = scaffold::scaffold(&ctx.cwd, &self.preset, self.force).map_err(|e| match e {
            scaffold::InitError::Exists => {
                tracing::info!("init: crunk.toml already present");
                CliError::Usage("init: crunk.toml already present; use --force".to_owned())
            }
            other => {
                tracing::warn!(error = %other, "init failed");
                CliError::from(
                    Refusal::new("E-INIT", RefusalClass::GuardNeedsAction, other.to_string())
                        .with_remedy("fix the cause above, then rerun"),
                )
            }
        })?;
        let mut rows: Vec<String> = data.written.iter().map(|p| format!("wrote {p}")).collect();
        if !data.detected.is_empty() {
            rows.push(format!("detected: {}", data.detected.join(", ")));
        }
        Ok(Payload::new(data).with_rendered(rows))
    }
}
