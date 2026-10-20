//! `config --for FILE` and `config diff --base REF`: the packs and rules in effect for one file and the config line each came from.
//!
//! Answers "where does this rule come from" (plugins.md section 2) from the one root
//! `grimble.toml` alone: path-scoped `[[packs.enable]]` entries and the `[packs] enabled` list are
//! resolved by `gob_packs::Activation`, and each active pack lists the registry rules whose
//! provenance names it. Standard rules are always on and are not repeated per file.

// frob:ticket 01M3ZX7K04VN51PGCXT9DCYMWB

use std::path::{Component, Path, PathBuf};

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_packs::Activation;
use gob_path::{RelPath, Shown};
use gob_rules::{Registry, RuleRow};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;
use crate::config_diff::{ConfigData, config_diff};
use crate::workspace::locate_root;

/// Show the packs and rules in effect for a file and the `grimble.toml` line that activated each pack.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "config",
    product = "grimble",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ConfigFor {
    /// `config diff`: the base ref, when this is a diff.
    diff_base: Option<String>,
    /// `config diff`: the head ref; the working copy when absent.
    diff_head: Option<String>,
    /// `config --for`: the file to explain.
    file: Option<String>,
}

/// One rule a pack contributes to a file.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct RuleInEffect {
    /// Rule id.
    pub id: String,
    /// Kebab-case alias.
    pub slug: String,
    /// Default severity, lowercase.
    pub severity: String,
    /// One-line summary.
    pub summary: String,
}

/// A pack in effect for the file, with the config line that activated it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct PackInEffect {
    /// The pack name.
    pub name: String,
    /// The config file holding the activating entry.
    pub config_file: String,
    /// One-based line of the activating entry.
    pub config_line: usize,
    /// Whether the entry marked the pack required.
    pub required: bool,
    /// The rules this pack contributes.
    pub rules: Vec<RuleInEffect>,
}

/// Output of `config --for`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct ConfigForData {
    /// The file asked about, relative to the workspace root.
    pub file: String,
    /// Packs in effect, in config order; a file outside every path sees only the always-on packs.
    pub packs: Vec<PackInEffect>,
}

/// Resolve `file` (root-relative) against the activation text of `config_file`, listing rules from `rows`.
///
/// # Errors
/// PACK005 `PackError::Malformed` when the `[packs]` table of the config is malformed.
pub fn config_for(
    config_file: &str,
    config_text: &str,
    file: &str,
    rows: &[RuleRow],
) -> Result<ConfigForData, gob_packs::PackError> {
    let activation = Activation::parse(config_file, config_text)?;
    let packs: Vec<PackInEffect> = activation
        .resolve(file)
        .into_iter()
        .map(|a| PackInEffect {
            rules: rows
                .iter()
                .filter(|r| r.pack == a.name)
                .map(|r| RuleInEffect {
                    id: r.id.to_owned(),
                    slug: r.slug.to_owned(),
                    severity: format!("{:?}", r.severity).to_lowercase(),
                    summary: r.summary.to_owned(),
                })
                .collect(),
            name: a.name,
            config_file: a.file,
            config_line: a.line,
            required: a.required,
        })
        .collect();
    tracing::info!(file, packs = packs.len(), "config --for resolved");
    Ok(ConfigForData {
        file: file.to_owned(),
        packs,
    })
}

/// `arg` made relative to `root` (lexically, against `cwd` when relative), or `None` when it lies outside.
fn root_relative(root: &Path, cwd: &Path, arg: &str) -> Option<String> {
    let mut full = PathBuf::new();
    for c in cwd.join(arg).components() {
        match c {
            Component::ParentDir => {
                full.pop();
            }
            Component::CurDir => {}
            other => full.push(other),
        }
    }
    RelPath::from_host(root, &full)
        .ok()
        .map(|rel| rel.as_str().to_owned())
}

/// `ConfigFor` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ConfigForArgs {
    #[arg(
        value_name = "ACTION",
        value_parser = ["diff"],
        help = "`diff` compares the policy at --base with --head"
    )]
    action: Option<String>,
    #[arg(
        long = "for",
        value_name = "FILE",
        conflicts_with = "action",
        required_unless_present = "action",
        help = "File to explain, relative to the current directory"
    )]
    file: Option<String>,
    #[arg(
        long,
        value_name = "REF",
        requires = "action",
        required_if_eq("action", "diff"),
        help = "diff: the ref whose policy is the baseline"
    )]
    base: Option<String>,
    #[arg(
        long,
        value_name = "REF",
        requires = "action",
        help = "diff: the ref to compare (default: the working copy)"
    )]
    head: Option<String>,
}

impl ConfigFor {
    /// `config --for FILE`.
    fn run_for(file: &str, ctx: &Context) -> Outcome<ConfigData> {
        let root = locate_root(&ctx.cwd);
        let Some(rel) = root_relative(&root, &ctx.cwd, file) else {
            return Err(CliError::Usage(format!(
                "{file} is outside the workspace root {}",
                Shown::of(&root)
            )));
        };
        let config_file = format!("{PRODUCT}.toml");
        let text = match std::fs::read_to_string(root.join(&config_file)) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                tracing::debug!("no {config_file}; no packs are activated");
                String::new()
            }
            Err(e) => {
                return Err(CliError::internal(format!(
                    "cannot read {config_file}: {e}"
                )));
            }
        };
        let data =
            config_for(&config_file, &text, &rel, &Registry::global().rows()).map_err(|e| {
                CliError::from(
                    Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, e.to_string())
                        .with_remedy(format!("fix {config_file} as described, then rerun")),
                )
            })?;
        let mut rows = vec![format!("{}: packs in effect", data.file)];
        for p in &data.packs {
            rows.push(format!(
                "  {} ({}:{}){}",
                p.name,
                p.config_file,
                p.config_line,
                if p.required { " required" } else { "" }
            ));
            rows.extend(
                p.rules
                    .iter()
                    .map(|r| format!("    {} {} {}", r.id, r.severity, r.summary)),
            );
        }
        Ok(Payload::new(ConfigData::For(data)).with_rendered(rows))
    }

    /// `config diff --base REF [--head REF]`.
    fn run_diff(base: &str, head: Option<&str>, ctx: &Context) -> Outcome<ConfigData> {
        let root = locate_root(&ctx.cwd);
        let config_file = format!("{PRODUCT}.toml");
        let repo = gob_git::Repo::discover(&root)
            .map_err(|e| CliError::Usage(format!("config diff needs a git repository: {e}")))?;
        let at_ref = |rev: &str| -> Result<String, CliError> {
            let blob = repo
                .read_blob_at(rev, &config_file)
                .map_err(|e| CliError::Usage(format!("cannot read {config_file} at {rev}: {e}")))?;
            Ok(blob
                .map(|b| String::from_utf8_lossy(&b).into_owned())
                .unwrap_or_default())
        };
        let base_text = at_ref(base)?;
        let (head_label, head_text) = match head {
            Some(h) => (h, at_ref(h)?),
            None => (
                "worktree",
                std::fs::read_to_string(root.join(&config_file)).unwrap_or_default(),
            ),
        };
        let data = config_diff(base, &base_text, head_label, &head_text).map_err(|e| {
            CliError::from(
                Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, e.to_string())
                    .with_remedy(format!("fix {config_file} as described, then rerun")),
            )
        })?;
        let show = |v: &Option<String>| v.clone().unwrap_or_else(|| "(unset)".to_owned());
        let mut rows = vec![format!(
            "{} -> {}: {} policy change(s), {} weakening(s)",
            data.base,
            data.head,
            data.changes.len(),
            data.weakenings.len()
        )];
        rows.extend(data.changes.iter().map(|c| {
            let weak = data.weakenings.iter().any(|w| w.key == c.key);
            format!(
                "  {}{}: {} -> {}",
                if weak { "[weakened] " } else { "" },
                c.key,
                show(&c.old),
                show(&c.new)
            )
        }));
        Ok(Payload::new(ConfigData::Diff(data)).with_rendered(rows))
    }
}

impl Command for ConfigFor {
    type Data = ConfigData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ConfigForArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ConfigForArgs>(m)?;
        Ok(if a.action.is_some() {
            Self {
                diff_base: a.base,
                diff_head: a.head,
                file: None,
            }
        } else {
            Self {
                file: a.file,
                ..Self::default()
            }
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ConfigData> {
        match (&self.diff_base, &self.file) {
            (Some(base), _) => Self::run_diff(base, self.diff_head.as_deref(), ctx),
            (None, Some(file)) => Self::run_for(file, ctx),
            (None, None) => Err(CliError::Usage(
                "config needs --for FILE or `diff --base REF`".to_owned(),
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const CFG: &str = "[[packs.enable]]\nname = \"react\"\npaths = [\"frontend/**\"]\n\n[[packs.enable]]\nname = \"core\"\nrequired = true\n";

    fn pack_rows() -> Vec<RuleRow> {
        let mut r = Registry::global()
            .rows()
            .into_iter()
            .next()
            .expect("std registry is not empty");
        r.pack = "react".to_owned();
        vec![r]
    }

    // frob:tests crates/grimble/src/config_for.rs::config_for
    #[test]
    fn react_and_its_rules_are_listed_with_the_config_line() {
        let rows = pack_rows();
        let d = config_for("grimble.toml", CFG, "frontend/a.tsx", &rows).unwrap();
        let react = d.packs.iter().find(|p| p.name == "react").unwrap();
        assert_eq!(react.config_line, 1);
        assert_eq!(react.config_file, "grimble.toml");
        assert_eq!(react.rules.len(), 1);
        assert_eq!(react.rules[0].id, rows[0].id);
    }

    // frob:tests crates/grimble/src/config_for.rs::config_for
    #[test]
    fn a_file_outside_every_path_sees_only_always_on_packs() {
        let d = config_for("grimble.toml", CFG, "backend/b.ts", &pack_rows()).unwrap();
        let names: Vec<_> = d.packs.iter().map(|p| p.name.as_str()).collect();
        assert_eq!(names, ["core"]);
        assert!(d.packs[0].required);
    }

    // frob:tests crates/grimble/src/config_for.rs::root_relative
    #[test]
    fn root_relative_is_lexical_and_rejects_escapes() {
        let root = Path::new("/r");
        assert_eq!(
            root_relative(root, Path::new("/r/sub"), "../a/./b.ts").as_deref(),
            Some("a/b.ts")
        );
        assert_eq!(root_relative(root, Path::new("/r"), "../x"), None);
    }
}
