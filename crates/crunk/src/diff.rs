//! `diff OTHER`: compare this project's generated tokens with another spec's.
//!
//! `OTHER` is a directory holding a `crunk.toml` (or the file itself), relative to the working
//! directory. Differences are data, not failure: the verb exits 0 either way.

// frob:ticket 01M43ATD7ZGTNCY5036AYEJR7P

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use crunk_spec::DesignSpec;
use crunk_tokens::TokenSet;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// List the tokens added, removed or changed in another spec.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "diff",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Diff {
    other: PathBuf,
}

/// `Diff` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DiffArgs {
    #[arg(
        value_name = "OTHER",
        help = "Spec directory (or crunk.toml) to compare against"
    )]
    other: PathBuf,
}

/// A token present on both sides with different values.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Changed {
    /// The custom-property name, with its leading `--`.
    pub name: String,
    /// The value in this project.
    pub current: String,
    /// The value in `OTHER`.
    pub other: String,
}

/// A token present on one side only.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Entry {
    /// The custom-property name, with its leading `--`.
    pub name: String,
    /// Its value.
    pub value: String,
}

/// Output of `diff`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, JsonSchema)]
pub struct DiffData {
    /// Tokens only `OTHER` defines.
    pub added: Vec<Entry>,
    /// Tokens only this project defines.
    pub removed: Vec<Entry>,
    /// Tokens both define with different values.
    pub changed: Vec<Changed>,
}

impl Command for Diff {
    type Data = DiffData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<DiffArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DiffArgs>(m)?;
        Ok(Self { other: a.other })
    }

    fn run(&self, ctx: &Context) -> Outcome<DiffData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let current = crunk_spec::load_spec(&root).map_err(|e| spec_refusal("crunk.toml", &e))?;
        let other_path = ctx.cwd.join(&self.other);
        let (file, other_root) = if other_path.is_dir() {
            (other_path.join("crunk.toml"), other_path)
        } else {
            let dir = other_path
                .parent()
                .map_or_else(|| ctx.cwd.clone(), Path::to_path_buf);
            (other_path, dir)
        };
        let other = crunk_spec::load_spec_file(&file, &other_root)
            .map_err(|e| spec_refusal(&file.to_string_lossy(), &e))?;
        let data = diff(&current, &other)?;
        tracing::info!(
            added = data.added.len(),
            removed = data.removed.len(),
            changed = data.changed.len(),
            "diff computed"
        );
        let rows = rows(&data);
        Ok(Payload::new(data).with_rendered(rows))
    }
}

fn spec_refusal(what: &str, err: &dyn std::fmt::Display) -> Refusal {
    tracing::info!(what, error = %err, "diff: spec did not load");
    Refusal::new(
        "E-SPEC",
        RefusalClass::GuardNeedsAction,
        format!("{what} is not a valid design spec: {err}"),
    )
    .with_remedy("fix the spec as described, then rerun")
}

fn token_map(spec: &DesignSpec) -> Result<BTreeMap<String, String>, Refusal> {
    let set = TokenSet::from_spec(spec).map_err(|e| {
        Refusal::new("E-TOKENS", RefusalClass::GuardNeedsAction, e.to_string())
            .with_remedy("rename one of the colliding entries in crunk.toml")
    })?;
    Ok(set
        .css_entries()
        .into_iter()
        .map(|(name, value)| (name.to_owned(), value))
        .collect())
}

/// Compare the generated tokens of two specs.
///
/// # Errors
///
/// A [`Refusal`] when either spec yields colliding token names.
pub fn diff(current: &DesignSpec, other: &DesignSpec) -> Result<DiffData, Refusal> {
    let (a, b) = (token_map(current)?, token_map(other)?);
    let mut data = DiffData::default();
    for (name, value) in &b {
        match a.get(name) {
            None => data.added.push(Entry {
                name: name.clone(),
                value: value.clone(),
            }),
            Some(cur) if cur != value => data.changed.push(Changed {
                name: name.clone(),
                current: cur.clone(),
                other: value.clone(),
            }),
            Some(_) => {}
        }
    }
    for (name, value) in &a {
        if !b.contains_key(name) {
            data.removed.push(Entry {
                name: name.clone(),
                value: value.clone(),
            });
        }
    }
    Ok(data)
}

/// Output lines: `+ NAME VALUE`, `- NAME VALUE`, `~ NAME CURRENT -> OTHER`, sorted by name.
fn rows(data: &DiffData) -> Vec<String> {
    let mut lines: Vec<(&str, String)> = Vec::new();
    for e in &data.added {
        lines.push((&e.name, format!("+ {} {}", e.name, e.value)));
    }
    for e in &data.removed {
        lines.push((&e.name, format!("- {} {}", e.name, e.value)));
    }
    for c in &data.changed {
        lines.push((
            &c.name,
            format!("~ {} {} -> {}", c.name, c.current, c.other),
        ));
    }
    if lines.is_empty() {
        return vec!["no differences".to_owned()];
    }
    lines.sort_by(|x, y| x.0.cmp(y.0));
    lines.into_iter().map(|(_, l)| l).collect()
}
