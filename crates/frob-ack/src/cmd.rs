//! The `ack`, `graph why` and `graph affects` verbs.

use std::collections::BTreeMap;
use std::path::PathBuf;

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{Cli, CliError, Command, Context, Outcome, Payload};
use gob_git::Repo;
use gob_symbols::{SymbolRecord, Symref};
use gob_walk::ContentSource;
use schemars::JsonSchema;
use serde::Serialize;

use crate::ack::{ack, plan_ack};
use crate::error::AckError;
use crate::inputs::{Inputs, section_digest};
use crate::rules::{Raw, raw_all};

/// Adds the frob-ack verbs to a product root.
pub fn register(cli: Cli) -> Cli {
    cli.register::<Ack>()
        .register::<GraphWhy>()
        .register::<GraphAffects>()
}

/// The work tree root containing `ctx.cwd`, else `ctx.cwd`.
fn root_of(ctx: &Context) -> PathBuf {
    Repo::discover(&ctx.cwd)
        .ok()
        .and_then(|r| r.work_dir().map(std::path::Path::to_path_buf))
        .unwrap_or_else(|| ctx.cwd.clone())
}

fn text_arg(name: &'static str, help: &'static str) -> Arg {
    Arg::new(name).long(name).value_name("TEXT").help(help)
}

/// Output of `ack`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AckData {
    /// Symrefs whose lock entry was added or changed.
    pub acked: Vec<String>,
    /// The commit that recorded the lock, when one was made.
    pub commit: Option<String>,
    /// The branch committed on.
    pub branch: Option<String>,
    /// The lock file, repo-relative.
    pub lock_file: String,
    /// True when nothing was written because of `--dry-run`.
    pub dry_run: bool,
}

/// Acknowledge symbols: record their digests in frob.lock and commit it on the current branch.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ack",
    product = "frob",
    dry_run,
    exits(ok, usage, refused, internal)
)]
pub struct Ack {
    targets: Vec<String>,
    all: bool,
    reason: Option<String>,
}

impl Command for Ack {
    type Data = AckData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("targets")
                .num_args(0..)
                .value_name("SYMREF|PATH")
                .help("Symbols to acknowledge; a path means every symbol in the file"),
        )
        .arg(
            Arg::new("all")
                .long("all")
                .action(ArgAction::SetTrue)
                .help("Re-ack every acked symbol and every frob:doc binding"),
        )
        .arg(text_arg("reason", "Why the current state is acknowledged"))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            targets: m
                .get_many::<String>("targets")
                .map(|v| v.cloned().collect())
                .unwrap_or_default(),
            all: m.get_flag("all"),
            reason: m.get_one::<String>("reason").cloned(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AckData> {
        let root = root_of(ctx);
        let data = if ctx.dry_run {
            let plan = plan_ack(
                &root,
                &self.targets,
                self.all,
                self.reason.as_deref(),
                ctx.clock.now(),
            )?;
            AckData {
                acked: plan.acked,
                commit: None,
                branch: None,
                lock_file: crate::inputs::PRODUCT.to_owned() + ".lock",
                dry_run: true,
            }
        } else {
            let out = ack(
                &root,
                &self.targets,
                self.all,
                self.reason.as_deref(),
                ctx.clock.now(),
            )?;
            AckData {
                acked: out.acked,
                commit: out.commit,
                branch: out.branch,
                lock_file: out.lock_file,
                dry_run: false,
            }
        };
        let already = data.acked.is_empty();
        Ok(Payload::new(data).with_already(already))
    }
}

/// Resolves a symbol or a whole-file path for the query verbs.
fn resolve_one<'g>(inputs: &'g Inputs, input: &str) -> Result<&'g SymbolRecord, AckError> {
    if !input.contains("::")
        && !input.contains('#')
        && let Some(r) = inputs.graph.get(&Symref::file(input))
    {
        return Ok(r);
    }
    inputs
        .graph
        .resolve(input)
        .map_err(|source| AckError::Resolve {
            input: input.to_owned(),
            source,
        })
}

/// One `frob:doc` directive involving the explained symbol.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BindingView {
    /// `bound` when the symbol carries the directive, `target` when it is the doc section.
    pub role: String,
    /// File holding the directive.
    pub file: String,
    /// 1-based line of the directive.
    pub line: u32,
    /// The bound symbol.
    pub symbol: String,
    /// The named doc section.
    pub target: String,
    /// Whether the named section exists now.
    pub target_exists: bool,
}

/// The recorded ack of the explained symbol.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AckView {
    /// Who acked.
    pub acked_by: String,
    /// When.
    pub acked_at: String,
    /// The reason given.
    pub reason: Option<String>,
    /// Facets whose current digest differs from the recorded one (`sig`, `body`, `doc`, `target`).
    pub changed_facets: Vec<String>,
}

/// One finding about the explained symbol.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct WhyFinding {
    /// The rule id.
    pub rule: String,
    /// The severity.
    pub severity: String,
    /// The message.
    pub message: String,
}

/// Output of `graph why`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct WhyData {
    /// The resolved symref.
    pub symbol: String,
    /// Its kind.
    pub kind: String,
    /// `frob:doc` directives that bind it or name it.
    pub bindings: Vec<BindingView>,
    /// Its lock entry, if acked.
    pub ack: Option<AckView>,
    /// Findings that fire for it.
    pub findings: Vec<WhyFinding>,
}

fn line_of(root: &std::path::Path, file: &str, offset: u32) -> u32 {
    // Offsets are into the git-normalized text (see `inputs::scan_file`).
    let Ok(text) = ContentSource::locate(root).with_reader(|r| r.read_text(file)) else {
        return 0;
    };
    let newlines = text
        .get(..offset as usize)
        .map_or(0, |s| s.matches('\n').count());
    u32::try_from(newlines + 1).unwrap_or(u32::MAX)
}

fn changed_facets(inputs: &Inputs, rec: &SymbolRecord) -> Vec<String> {
    let Some(e) = inputs.lock.entries.get(&rec.symref.to_string()) else {
        return Vec::new();
    };
    let d = &rec.digests;
    let mut out = Vec::new();
    for (name, now, was) in [
        ("sig", d.sig.to_string(), &e.sig),
        ("body", d.body.to_string(), &e.body),
        ("doc", d.doc.to_string(), &e.doc),
        ("attr", d.attr.to_string(), &e.attr),
    ] {
        if &now != was {
            out.push(name.to_owned());
        }
    }
    let target_moved = e.targets.iter().any(|t| {
        Symref::parse(&t.target)
            .ok()
            .and_then(|s| inputs.graph.get(&s))
            .is_some_and(|r| section_digest(&r.digests).to_string() != t.digest)
    });
    if target_moved {
        out.push("target".to_owned());
    }
    out
}

/// Explain the bindings and acks that make a finding fire for a symbol.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "graph why",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct GraphWhy {
    symbol: String,
}

impl Command for GraphWhy {
    type Data = WhyData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("symbol")
                .required(true)
                .value_name("SYMREF")
                .help("Symref, path or unique name suffix"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            symbol: m.get_one::<String>("symbol").cloned().unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<WhyData> {
        let root = root_of(ctx);
        let inputs = Inputs::collect(&root)?;
        let rec = resolve_one(&inputs, &self.symbol)?;
        let bindings = inputs
            .docs
            .iter()
            .filter(|d| d.involves(&rec.symref))
            .map(|d| BindingView {
                role: if d.symbol == rec.symref {
                    "bound"
                } else {
                    "target"
                }
                .to_owned(),
                file: d.file.clone(),
                line: line_of(&root, &d.file, u32::from(d.span.range.start())),
                symbol: d.symbol.to_string(),
                target: d.target.to_string(),
                target_exists: inputs.graph.get(&d.target).is_some(),
            })
            .collect();
        let ack = inputs
            .lock
            .entries
            .get(&rec.symref.to_string())
            .map(|e| AckView {
                acked_by: e.acked_by.clone(),
                acked_at: e.acked_at.clone(),
                reason: e.reason.clone(),
                changed_facets: changed_facets(&inputs, rec),
            });
        let anchor = rec.symref.to_string();
        let raws: Vec<Raw> = raw_all(&inputs)
            .into_iter()
            .filter(|r| r.anchor == anchor)
            .collect();
        let findings = raws
            .iter()
            .map(|r| WhyFinding {
                rule: r.meta.id.to_owned(),
                severity: format!("{:?}", r.severity),
                message: r.message.clone(),
            })
            .collect();
        tracing::info!(symbol = %anchor, "graph why");
        Ok(Payload::new(WhyData {
            symbol: anchor,
            kind: format!("{:?}", rec.kind),
            bindings,
            ack,
            findings,
        }))
    }
}

/// Output of `graph affects`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AffectsData {
    /// The resolved symref.
    pub symbol: String,
    /// Number of affected symbols.
    pub count: usize,
    /// Affected symrefs grouped by file, both sorted.
    pub files: BTreeMap<String, Vec<String>>,
}

/// List the transitive dependents of a symbol, grouped by file.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "graph affects",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct GraphAffects {
    symbol: String,
}

impl Command for GraphAffects {
    type Data = AffectsData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("symbol")
                .required(true)
                .value_name("SYMREF")
                .help("Symref, path or unique name suffix"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            symbol: m.get_one::<String>("symbol").cloned().unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AffectsData> {
        let inputs = Inputs::collect(&root_of(ctx))?;
        let rec = resolve_one(&inputs, &self.symbol)?;
        let affected = inputs.graph.affects(&rec.symref);
        let mut files: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for s in &affected {
            files
                .entry(s.path().to_owned())
                .or_default()
                .push(s.to_string());
        }
        tracing::info!(symbol = %rec.symref, count = affected.len(), "graph affects");
        Ok(Payload::new(AffectsData {
            symbol: rec.symref.to_string(),
            count: affected.len(),
            files,
        }))
    }
}
