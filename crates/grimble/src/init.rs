//! `init`: materialize `grimble.toml`, ignore `.grimble/` and seed an empty model; safe to repeat.

use std::path::Path;

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_config::materialize;
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{check_error, config_refusal, locate_root, registered_tables};

/// The model file `init` seeds when the repository has no model.
pub const MODEL_PATH: &str = "design/model.grmb";
/// The seed text: the version header and nothing else (grmb-spec 2.1).
pub const MODEL_SEED: &str = "grimble = \"2\";\n";
/// Lines that already ignore the state directory.
const IGNORE_FORMS: [&str; 4] = [".grimble/", ".grimble", "/.grimble/", "/.grimble"];

/// Write grimble.toml knobs, ignore `.grimble/` and seed `design/model.grmb`; safe to repeat.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "init",
    product = "grimble",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Init;

/// One file step of init.
#[derive(Debug, Serialize, JsonSchema)]
pub struct Step {
    /// What the step touches.
    pub target: String,
    /// True when the step changed something.
    pub changed: bool,
}

/// What materializing `grimble.toml` did.
#[derive(Debug, Serialize, JsonSchema)]
pub struct ConfigStep {
    /// The config file.
    pub path: String,
    /// Full dotted keys added.
    pub added: Vec<String>,
    /// True when the file did not exist and was created.
    pub created: bool,
}

/// Output of `init`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct InitData {
    /// Repository root initialized.
    pub root: String,
    /// The materialized config file.
    pub config: ConfigStep,
    /// The seeded model file (unchanged when any model already exists).
    pub model: Step,
    /// The `.gitignore` entry.
    pub gitignore: Step,
}

fn internal(what: &str, path: &Path, e: &std::io::Error) -> CliError {
    CliError::internal(format!("cannot {what} {}: {e}", path.display()))
}

/// Seed `design/model.grmb` unless the repository already has a model file.
fn ensure_model(root: &Path) -> Result<Step, CliError> {
    let models = grimble_check::survey(root).map_err(check_error)?.models;
    let path = root.join(MODEL_PATH);
    let changed = models.is_empty() && !path.exists();
    if changed {
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir).map_err(|e| internal("create", dir, &e))?;
        }
        std::fs::write(&path, MODEL_SEED).map_err(|e| internal("write", &path, &e))?;
        tracing::info!(path = %path.display(), "model seeded");
    }
    Ok(Step {
        target: MODEL_PATH.to_owned(),
        changed,
    })
}

/// Ensure `.grimble/` is ignored; returns whether the file changed.
fn ensure_gitignore(root: &Path) -> Result<Step, CliError> {
    let path = root.join(".gitignore");
    let existing = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(e) => return Err(internal("read", &path, &e)),
    };
    let present = existing.lines().any(|l| IGNORE_FORMS.contains(&l.trim()));
    if !present {
        let mut text = existing;
        if !text.is_empty() && !text.ends_with('\n') {
            text.push('\n');
        }
        text.push_str(".grimble/\n");
        std::fs::write(&path, text).map_err(|e| internal("write", &path, &e))?;
        tracing::info!(path = %path.display(), "state directory ignored");
    }
    Ok(Step {
        target: ".gitignore".to_owned(),
        changed: !present,
    })
}

impl Command for Init {
    type Data = InitData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<InitData> {
        let root = locate_root(&ctx.cwd);
        let descs = registered_tables();
        let refs: Vec<&gob_config::TableDescription> = descs.iter().collect();
        let report = materialize(&root, crate::PRODUCT, &refs).map_err(|e| config_refusal(&e))?;
        let config = ConfigStep {
            path: report.path.display().to_string(),
            added: report.added,
            created: report.created,
        };
        let model = ensure_model(&root)?;
        let gitignore = ensure_gitignore(&root)?;
        let already = config.added.is_empty() && !model.changed && !gitignore.changed;
        tracing::info!(already, "init finished");
        Ok(Payload::new(InitData {
            root: root.display().to_string(),
            config,
            model,
            gitignore,
        })
        .with_already(already))
    }
}
