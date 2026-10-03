//! `doctor`: fidelity per language, model parse status and config status.

use std::collections::BTreeMap;

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_check::config::{ComputeTable, PacksTable};
use grimble_check::fidelity::{capabilities_of, known_adapters};
use grimble_check::model_view::file_row;
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{check_error, locate_root};

/// Report adapter fidelity per language, how each model file parses and the state of grimble.toml.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "doctor",
    product = "grimble",
    exits(ok, refused, usage, internal)
)]
pub struct Doctor;

/// One language adapter.
#[derive(Debug, Serialize, JsonSchema)]
pub struct LanguageRow {
    /// Language tag.
    pub language: String,
    /// Adapter identity (name, version, grammar).
    pub adapter: String,
    /// Fidelity level `F0` to `F4`.
    pub fidelity: String,
    /// Walked files this adapter claims.
    pub files: usize,
    /// Capability atom to precision word.
    pub capabilities: BTreeMap<String, String>,
}

/// One model file.
#[derive(Debug, Serialize, JsonSchema)]
pub struct ModelRow {
    /// Repo-relative path.
    pub path: String,
    /// `parsed`, `opaque` or `refused`.
    pub status: String,
    /// Why, for `opaque` and `refused`.
    pub reason: Option<String>,
    /// Syntax holes.
    pub holes: usize,
}

/// State of `grimble.toml`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct ConfigRow {
    /// True when `grimble.toml` exists.
    pub present: bool,
    /// `ok`, or the first config error.
    pub status: String,
    /// The product file `[compute]` is read from (`frob` or `grimble`).
    pub compute_source: Option<String>,
    /// The `compute_digest` in force.
    pub compute_digest: Option<String>,
    /// Pack ids enabled in `[packs]`.
    pub packs_enabled: Vec<String>,
    /// True when packs are enabled; they are not loaded by this build.
    pub packs_unloaded: bool,
}

/// Output of `doctor`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct DoctorData {
    /// Repository root.
    pub root: String,
    /// `grimble.toml` state.
    pub config: ConfigRow,
    /// Model files and how they parse.
    pub model: Vec<ModelRow>,
    /// Every adapter with its fidelity and file count.
    pub languages: Vec<LanguageRow>,
}

fn config_row(root: &std::path::Path) -> ConfigRow {
    let present = root.join("grimble.toml").is_file();
    let loaded =
        ComputeTable::load_for(root).and_then(|(c, src)| Ok((c, src, PacksTable::load(root)?)));
    match loaded {
        Ok((compute, source, packs)) => ConfigRow {
            present,
            status: "ok".to_owned(),
            compute_source: Some(source.to_owned()),
            compute_digest: Some(compute.digest()),
            packs_unloaded: packs.requests_packs(),
            packs_enabled: packs.enabled,
        },
        Err(e) => ConfigRow {
            present,
            status: e.to_string(),
            compute_source: None,
            compute_digest: None,
            packs_enabled: Vec::new(),
            packs_unloaded: false,
        },
    }
}

impl Command for Doctor {
    type Data = DoctorData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<DoctorData> {
        let root = locate_root(&ctx.cwd);
        let survey = grimble_check::survey(&root).map_err(check_error)?;
        let mut model = Vec::new();
        for path in &survey.models {
            let bytes = std::fs::read(root.join(path)).unwrap_or_default();
            let row = file_row(path, &bytes);
            model.push(ModelRow {
                path: row.path,
                status: row.status.to_owned(),
                reason: row.reason,
                holes: row.holes,
            });
        }
        let languages = known_adapters()
            .into_iter()
            .map(|a| LanguageRow {
                language: a.language().to_owned(),
                adapter: a.identity(),
                fidelity: a.fidelity().to_string(),
                files: survey.languages.get(a.language()).copied().unwrap_or(0),
                capabilities: capabilities_of(a.language())
                    .into_iter()
                    .map(|(k, v)| (k, v.to_owned()))
                    .collect(),
            })
            .collect();
        let config = config_row(&root);
        let mut payload = Payload::new(DoctorData {
            root: root.display().to_string(),
            config,
            model,
            languages,
        });
        if payload.data.config.packs_unloaded {
            payload
                .warnings
                .push(grimble_check::config::PACKS_NOT_LOADED.to_owned());
        }
        tracing::info!("doctor finished");
        Ok(payload)
    }
}
