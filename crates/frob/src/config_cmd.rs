//! `config show --effective` and `config sync`.

use std::path::{Path, PathBuf};

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_config::{TableDescription, materialize};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;
use crate::config::FrobConfig;
use crate::init::detected_default;
use crate::workspace::{Located, config_refusal, registered_tables, table_refs};

/// What a materialize (or its dry run) did to `frob.toml`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct SyncData {
    /// The config file written, or that would be.
    pub path: String,
    /// Full dotted keys added, or that would be added.
    pub added: Vec<String>,
    /// True when the file did not exist and was (or would be) created.
    pub created: bool,
    /// True when nothing was written because of `--dry-run`.
    pub dry_run: bool,
}

/// Dotted keys of enforcement knobs absent from `<root>/frob.toml`.
fn missing_knobs(
    root: &Path,
    tables: &[&TableDescription],
) -> Result<(Vec<String>, bool), CliError> {
    let path = root.join(format!("{PRODUCT}.toml"));
    let (doc, present) = match std::fs::read_to_string(&path) {
        Ok(text) => (
            text.parse::<toml::Table>().map_err(|e| {
                config_refusal(&gob_config::ConfigError::Parse {
                    path: path.clone(),
                    message: e.to_string(),
                })
            })?,
            true,
        ),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => (toml::Table::new(), false),
        Err(source) => {
            return Err(config_refusal(&gob_config::ConfigError::Io {
                path,
                source,
            }));
        }
    };
    let mut missing = Vec::new();
    for desc in tables.iter().filter(|d| d.materialize) {
        let table = desc
            .table
            .split('.')
            .try_fold(&doc, |t, seg| t.get(seg)?.as_table());
        for f in desc.fields.iter().filter(|f| f.enforcement) {
            if !table.is_some_and(|t| t.contains_key(&f.key)) {
                missing.push(format!("{}.{}", desc.table, f.key));
            }
        }
    }
    Ok((missing, present))
}

/// Supplies the repository-detected default for a missing dotted knob, or `None` to keep the static default; never called for a present knob.
pub(crate) type Detect<'a> = &'a dyn Fn(&str) -> Result<Option<toml::Value>, CliError>;

/// Write every missing materialized knob of all registered tables; `detect` (when given) replaces the static default of each absent knob it answers for.
pub(crate) fn sync_config(
    root: &Path,
    dry_run: bool,
    detect: Option<Detect<'_>>,
) -> Result<SyncData, CliError> {
    let mut descs = registered_tables();
    if let Some(detect) = detect {
        let refs = table_refs(&descs);
        let (missing, _) = missing_knobs(root, &refs)?;
        for key in &missing {
            let Some(value) = detect(key)? else { continue };
            tracing::info!(key, %value, "knob default detected from the repository");
            for d in &mut descs {
                for f in &mut d.fields {
                    if format!("{}.{}", d.table, f.key) == *key {
                        f.default_toml = value.to_string();
                    }
                }
            }
        }
    }
    let refs = table_refs(&descs);
    if dry_run {
        let (added, present) = missing_knobs(root, &refs)?;
        tracing::info!(missing = added.len(), "config sync dry run");
        let created = !present && !added.is_empty();
        return Ok(SyncData {
            path: root.join("frob.toml").display().to_string(),
            added,
            created,
            dry_run,
        });
    }
    let report = materialize(root, PRODUCT, &refs).map_err(|e| config_refusal(&e))?;
    tracing::info!(
        added = report.added.len(),
        created = report.created,
        "config synced"
    );
    Ok(SyncData {
        path: report.path.display().to_string(),
        added: report.added,
        created: report.created,
        dry_run,
    })
}

/// Add every knob a materialized table is missing to `frob.toml`; comments are kept.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "config sync",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct ConfigSync;

impl Command for ConfigSync {
    type Data = SyncData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<SyncData> {
        let located = Located::discover(&ctx.cwd);
        // Outside a work tree there is nothing to detect; the static defaults apply.
        let root = &located.root;
        let detect = located
            .require_repo()
            .ok()
            .map(|repo| move |key: &str| detected_default(repo, root, key));
        let data = sync_config(
            &located.root,
            ctx.dry_run,
            detect.as_ref().map(|d| d as Detect<'_>),
        )?;
        let already = data.added.is_empty();
        Ok(Payload::new(data).with_already(already))
    }
}

/// One key of a table in the effective view.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct KeyView {
    /// Key name within its table.
    pub key: String,
    /// Effective value.
    pub value: serde_json::Value,
    /// Which layer supplied it: `default` or `file`.
    pub provenance: String,
    /// True when the knob is materialized by `frob init`.
    pub enforcement: bool,
}

/// One table in the effective view.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TableView {
    /// Dotted table path.
    pub table: String,
    /// Keys in declaration order.
    pub keys: Vec<KeyView>,
}

/// Output of `config show`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ShowData {
    /// The config file consulted.
    pub file: String,
    /// True when the file exists.
    pub file_present: bool,
    /// Every registered table, merged with provenance.
    pub tables: Vec<TableView>,
}

/// Print every config table merged (defaults, then frob.toml) with provenance.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "config show",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ConfigShow;

fn toml_json(v: &toml::Value) -> serde_json::Value {
    serde_json::to_value(v).unwrap_or(serde_json::Value::Null)
}

/// Convert an inline TOML value (as rendered by gob-config) to JSON.
fn inline_json(inline: &str) -> serde_json::Value {
    format!("v = {inline}")
        .parse::<toml::Table>()
        .ok()
        .and_then(|t| t.get("v").map(toml_json))
        .unwrap_or(serde_json::Value::Null)
}

impl Command for ConfigShow {
    type Data = ShowData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            gob_cli::clap::Arg::new("effective")
                .long("effective")
                .action(gob_cli::clap::ArgAction::SetTrue)
                .help("Show the merged effective values (the only view today)"),
        )
    }

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<ShowData> {
        let located = Located::discover(&ctx.cwd);
        let root = &located.root;
        // Typed load validates keys and values of frob's own tables first.
        FrobConfig::load(root).map_err(|e| config_refusal(&e))?;
        let file: PathBuf = root.join(format!("{PRODUCT}.toml"));
        let (doc, present) = match std::fs::read_to_string(&file) {
            Ok(text) => (
                text.parse::<toml::Table>().map_err(CliError::internal)?,
                true,
            ),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (toml::Table::new(), false),
            Err(e) => return Err(CliError::internal(e)),
        };
        let mut tables = Vec::new();
        for desc in registered_tables() {
            let in_file = desc
                .table
                .split('.')
                .try_fold(&doc, |t, seg| t.get(seg)?.as_table());
            let keys = desc
                .fields
                .iter()
                .map(|f| {
                    let from_file = in_file.and_then(|t| t.get(&f.key));
                    KeyView {
                        key: f.key.clone(),
                        value: from_file.map_or_else(|| inline_json(&f.default_toml), toml_json),
                        provenance: if from_file.is_some() {
                            "file"
                        } else {
                            "default"
                        }
                        .to_owned(),
                        enforcement: f.enforcement,
                    }
                })
                .collect();
            tables.push(TableView {
                table: desc.table,
                keys,
            });
        }
        Ok(Payload::new(ShowData {
            file: file.display().to_string(),
            file_present: present,
            tables,
        }))
    }
}
