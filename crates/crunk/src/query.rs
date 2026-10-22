//! `query KIND [ARG]`: find, component, dupes, unused, uses, color and violations over the project.
//!
//! Every kind but `violations` is a pure read over the ingested styles and the token set
//! ([`crunk_query`]). `violations` runs the check pipeline and lists its findings; it never
//! exits 1, because it reports the findings rather than judging them. An unknown `component`
//! or a missing or malformed argument is a usage error (exit 2).

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

use std::path::PathBuf;

use crunk_query::{
    ColorRow, ComponentRow, DEFAULT_DUPE_THRESHOLD, DupeRow, FindRow, Model, Site, UnusedRow,
};
use crunk_spec::DesignSpec;
use crunk_tokens::TokenSet;
use gob_cli::clap::{ArgMatches, builder::PossibleValuesParser};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// The query kinds.
pub const KINDS: [&str; 7] = [
    "find",
    "component",
    "dupes",
    "unused",
    "uses",
    "color",
    "violations",
];

/// Ask a question of the project: find, component, dupes, unused, uses, color or violations.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "query",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Query {
    kind: String,
    arg: Option<String>,
    threshold: Option<String>,
    rule: Option<String>,
    path: Option<String>,
    no_cache: bool,
}

/// One finding row of `query violations`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ViolationRow {
    /// Rule id, e.g. `TOKENS001`.
    pub rule: String,
    /// `unresolved`, `advisory`, `warn` or `error`.
    pub severity: String,
    /// Path relative to the project root; empty when the finding has no file.
    pub path: String,
    /// 1-based line; 0 when the finding has no position.
    pub line: u32,
    /// The finding message.
    pub message: String,
    /// True when `crunk check --fix` could repair it.
    pub fixable: bool,
    /// True when an exception suppressed it.
    pub waived: bool,
}

/// The rows of one query, by kind.
#[derive(Debug, Clone, Serialize, JsonSchema)]
#[serde(untagged)]
pub enum Results {
    /// `find` hits.
    Find(Vec<FindRow>),
    /// The one `component`.
    Component(Vec<ComponentRow>),
    /// `dupes` pairs.
    Dupes(Vec<DupeRow>),
    /// `unused` tokens.
    Unused(Vec<UnusedRow>),
    /// `uses` sites.
    Uses(Vec<Site>),
    /// `color` palette distances.
    Color(Vec<ColorRow>),
    /// `violations` findings.
    Violations(Vec<ViolationRow>),
}

/// Output of `query`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct QueryData {
    /// Which query ran.
    pub kind: String,
    /// Its rows.
    pub results: Results,
}

/// `Query` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct QueryArgs {
    #[arg(
        value_name = "KIND",
        value_parser = PossibleValuesParser::new(KINDS),
        help = "find, component, dupes, unused, uses, color or violations"
    )]
    kind: String,
    #[arg(
        value_name = "ARG",
        help = "The name (find, component, uses) or CSS color (color) to ask about"
    )]
    arg: Option<String>,
    #[arg(
        long,
        value_name = "SCORE",
        help = "dupes: minimum shared-declaration score, 0 to 1 (default 0.6)"
    )]
    threshold: Option<String>,
    #[arg(
        long,
        value_name = "RULE",
        help = "violations: keep one rule id or family"
    )]
    rule: Option<String>,
    #[arg(
        long,
        value_name = "GLOB",
        help = "violations: keep paths matching this glob"
    )]
    path: Option<String>,
    #[arg(
        long = "no-cache",
        help = "Accepted for parity; queries always ingest fresh"
    )]
    no_cache: bool,
}

/// What every crunk read verb loads: the root, the spec, the ingested styles and the tokens.
pub(crate) struct Loaded {
    /// The project root.
    pub root: PathBuf,
    /// The parsed spec.
    pub spec: DesignSpec,
    /// The ingested stylesheets.
    pub styles: crunk_ingest::ProjectStyles,
    /// The token set.
    pub tokens: TokenSet,
}

impl Loaded {
    /// The query model over the loaded data.
    pub(crate) fn model(&self) -> Model<'_> {
        Model::new(&self.styles, &self.tokens, &self.root)
    }
}

fn refusal(code: &str, message: &str) -> Refusal {
    Refusal::new(code, RefusalClass::GuardNeedsAction, message)
}

/// `path` with `.` and `..` components folded away, so it prefixes the ingest's normalized paths.
fn lexical(path: &std::path::Path) -> PathBuf {
    use std::path::Component;
    let mut out = PathBuf::new();
    for part in path.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

/// Locate the root, load the spec, ingest the tree and derive the tokens, or refuse.
pub(crate) fn load(verb: &str, ctx: &Context) -> Result<Loaded, CliError> {
    let root = lexical(&gob_product::workspace::locate_root(PRODUCT, &ctx.cwd));
    let spec = crunk_spec::load_spec(&root).map_err(|e| {
        tracing::info!(verb, error = %e, "spec did not load");
        refusal(
            "E-SPEC",
            &format!("crunk.toml is not a valid design spec: {e}"),
        )
        .with_remedy("fix crunk.toml as described, then rerun")
    })?;
    let ingested = crunk_ingest::ingest_tree(&spec, &gob_cache::Cache::null()).map_err(|e| {
        tracing::info!(verb, error = %e, "ingest failed");
        refusal("E-INGEST", &e.to_string()).with_remedy("fix the css_root path, then rerun")
    })?;
    let tokens = TokenSet::from_spec(&spec).map_err(|e| {
        tracing::info!(verb, error = %e, "token set failed");
        refusal("E-TOKENS", &e.to_string())
            .with_remedy("rename one of the colliding entries in crunk.toml")
    })?;
    tracing::debug!(
        verb,
        sheets = ingested.styles.sheets.len(),
        "project loaded"
    );
    Ok(Loaded {
        root,
        spec,
        styles: ingested.styles,
        tokens,
    })
}

impl Command for Query {
    type Data = QueryData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<QueryArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<QueryArgs>(m)?;
        Ok(Self {
            kind: a.kind,
            arg: a.arg,
            threshold: a.threshold,
            rule: a.rule,
            path: a.path,
            no_cache: a.no_cache,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<QueryData> {
        tracing::debug!(kind = %self.kind, no_cache = self.no_cache, "query");
        let threshold = self.threshold()?;
        let name = self.name_arg();
        let loaded = load("query", ctx)?;
        let model = loaded.model();
        let (results, lines) = match self.kind.as_str() {
            "find" => {
                let rows = model.find(&name?);
                let lines = rows
                    .iter()
                    .map(|r| format!("{:<9?} {:<6?} {:>4}  {}", r.matched, r.kind, r.uses, r.name))
                    .collect();
                (Results::Find(rows), lines)
            }
            "component" => {
                let name = name?;
                let row = model.component(&name).ok_or_else(|| {
                    CliError::Usage(format!("query component: no component named '{name}'"))
                })?;
                let lines = vec![format!(
                    "{}: {} element(s), {} modifier(s), {} declaration(s)",
                    row.name,
                    row.elements.len(),
                    row.modifiers.len(),
                    row.declarations
                )];
                (Results::Component(vec![row]), lines)
            }
            "dupes" => {
                let rows = model.dupes(threshold);
                let lines = rows
                    .iter()
                    .map(|r| format!("{:.2}  {}  {}  ({} shared)", r.score, r.a, r.b, r.shared))
                    .collect();
                (Results::Dupes(rows), lines)
            }
            "unused" => {
                let rows = model.unused();
                let lines = rows.iter().map(|r| r.name.clone()).collect();
                (Results::Unused(rows), lines)
            }
            "uses" => {
                let rows = model.uses(&name?);
                let lines = rows
                    .iter()
                    .map(|s| format!("{}:{}", s.path, s.line))
                    .collect();
                (Results::Uses(rows), lines)
            }
            "color" => {
                let value = name?;
                let rows = model.color(&value).ok_or_else(|| {
                    CliError::Usage(format!("query color: '{value}' is not a CSS color"))
                })?;
                let lines = rows
                    .iter()
                    .map(|r| format!("{:>8.2}  {:<24} {}", r.distance, r.name, r.value))
                    .collect();
                (Results::Color(rows), lines)
            }
            _ => {
                let rows = self.violations(&loaded)?;
                let lines = rows
                    .iter()
                    .map(|r| {
                        format!(
                            "{} {} {}:{} {}",
                            r.severity, r.rule, r.path, r.line, r.message
                        )
                    })
                    .collect();
                (Results::Violations(rows), lines)
            }
        };
        tracing::info!(kind = %self.kind, "query answered");
        let data = QueryData {
            kind: self.kind.clone(),
            results,
        };
        Ok(Payload::new(data).with_rendered(lines))
    }
}

impl Query {
    /// The `--threshold`, defaulting to [`DEFAULT_DUPE_THRESHOLD`]; usage error when not 0..=1.
    fn threshold(&self) -> Result<f64, CliError> {
        let Some(text) = &self.threshold else {
            return Ok(DEFAULT_DUPE_THRESHOLD);
        };
        match text.parse::<f64>() {
            Ok(v) if (0.0..=1.0).contains(&v) => Ok(v),
            _ => Err(CliError::Usage(format!(
                "--threshold must be a number from 0 to 1, got '{text}'"
            ))),
        }
    }

    /// The positional argument, or a usage error naming the kind that needs it.
    fn name_arg(&self) -> Result<String, CliError> {
        match (&self.arg, self.kind.as_str()) {
            (Some(arg), _) => Ok(arg.clone()),
            (None, "find" | "component" | "uses" | "color") => Err(CliError::Usage(format!(
                "query {} needs an argument",
                self.kind
            ))),
            (None, _) => Ok(String::new()),
        }
    }

    /// Run the check pipeline and list every finding (suppressed ones flagged `waived`).
    fn violations(&self, loaded: &Loaded) -> Result<Vec<ViolationRow>, CliError> {
        let run =
            crunk_check::run(&loaded.root, &crunk_check::CheckOptions::default()).map_err(|e| {
                tracing::info!(error = %e, "violations: check failed");
                refusal("E-CHECK", &e.to_string())
                    .with_remedy("fix the reported config, then rerun")
            })?;
        // Unresolved findings mark rules that could not run, not violations of the project.
        let active = run
            .report
            .findings
            .iter()
            .filter(|f| f.severity != gob_rules::Severity::Unresolved)
            .map(|f| (f, false));
        let waived = run.report.suppressed.iter().map(|(f, _)| (f, true));
        let mut rows: Vec<ViolationRow> = active
            .chain(waived)
            .map(|(f, waived)| {
                let (path, line) = match f.span {
                    Some(span) => {
                        let path = run.report.files.path(span.file).unwrap_or("").to_owned();
                        let start = u32::from(span.range.start());
                        // A finding anchored at offset 0 is about the whole file: line 0.
                        let line = if start == 0 {
                            0
                        } else {
                            line_of(&loaded.root, &path, start)
                        };
                        (path, line)
                    }
                    None => (String::new(), 0),
                };
                ViolationRow {
                    rule: f.rule.as_str().to_owned(),
                    severity: format!("{:?}", f.severity).to_lowercase(),
                    path,
                    line,
                    message: f.message.clone(),
                    fixable: f.fix.is_some(),
                    waived,
                }
            })
            .filter(|r| self.keeps(r))
            .collect();
        rows.sort_by(|a, b| (&a.path, a.line, &a.rule).cmp(&(&b.path, b.line, &b.rule)));
        tracing::debug!(rows = rows.len(), "violations collected");
        Ok(rows)
    }

    /// Whether `--rule` and `--path` keep `row`.
    fn keeps(&self, row: &ViolationRow) -> bool {
        let rule_ok = self.rule.as_deref().is_none_or(|rule| {
            row.rule.eq_ignore_ascii_case(rule)
                || row.rule.to_lowercase().starts_with(&rule.to_lowercase())
                    && rule.chars().all(|c| c.is_ascii_alphabetic())
        });
        let path_ok = self
            .path
            .as_deref()
            .is_none_or(|glob| crunk_ingest::glob::fnmatch(&row.path, glob));
        rule_ok && path_ok
    }
}

/// The 1-based line holding byte `offset` of `root/path`; 0 when the file cannot be read.
#[allow(
    clippy::disallowed_methods,
    reason = "a finding's line is read from the current source of the file it points into"
)]
pub(crate) fn line_of(root: &std::path::Path, path: &str, offset: u32) -> u32 {
    let Ok(bytes) = std::fs::read(root.join(path)) else {
        return 0;
    };
    let end = usize::try_from(offset)
        .unwrap_or(usize::MAX)
        .min(bytes.len());
    let newlines = bytes[..end].split(|b| *b == b'\n').count() - 1;
    u32::try_from(newlines + 1).unwrap_or(u32::MAX)
}
