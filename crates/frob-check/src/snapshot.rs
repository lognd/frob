//! frob's input collection, done once per run: graph, directives, lock and ledger (the walk is gob-check's).

use std::collections::BTreeSet;
use std::path::Path;
use std::time::Instant;

use frob_ack::{DocDirective, Inputs};
use frob_ledger::{Ledger, LedgerConfig};
use frob_obligations::{InvariantsConfig, ObligationInputs};
use gob_cache::{ArtifactKey, Cache};
use gob_check::{CollectCx, Collected};
use gob_directives::frob::Doc;
use gob_directives::{Binding, Directive, DirectiveRecord, ScanConfig, Scanner};
use gob_languages::{Language, grammar_identity};
use gob_lock::{LockFile, file_name};
use gob_rules::Finding;
use gob_symbols::{EXTRACTOR_VERSION, Symref, Target, build_graph_with_stats, extract_file};
use gob_text::{FileId, FileInterner};
use gob_walk::FileEntry;
use rayon::prelude::*;

use gob_check::CheckError;

use crate::options::CheckOptions;
use crate::product::Frob;

/// The product whose `frob.lock` and `.frob/` the check reads.
pub(crate) const PRODUCT: &str = "frob";

/// Substring that makes a file worth scanning for directives (cheap prefilter).
const DIRECTIVE_MARKER: &str = "frob:";

/// The ledger and the commit it was read at.
pub(crate) struct LedgerState {
    /// The open ledger.
    pub ledger: Ledger,
    /// Ledger tip commit, hex; the side-input digest of ledger-reading rules.
    pub tip: String,
    /// Tickets the ledger held at `tip`; the subjects of the ledger-reading `must_measure` rules.
    pub tickets: usize,
    /// Milestone objects at `tip`; `PM034` is not applicable at zero.
    pub milestones: usize,
}

/// Thread-safe facts frob's checks read while deciding applicability and cache keys.
pub struct FrobShared {
    /// Ledger tip commit (hex), or the empty string without a ledger.
    pub ledger_tip: String,
    /// Files the obligation rules evaluate: graph file nodes plus files holding a directive.
    pub obligation_paths: BTreeSet<String>,
    /// True when a ledger is open (the ledger-reading rules can run).
    pub has_ledger: bool,
    /// Fidelity and parse facts of every walked file, by path.
    pub file_info: std::collections::BTreeMap<String, gob_symbols::FileInfo>,
}

/// Everything frob's rules read besides the walk, built once per pass.
pub struct FrobInputs {
    /// Repository root.
    pub(crate) root: std::path::PathBuf,
    /// Graph, lock, `frob:doc` directives and the shared interner (frob-ack's input bundle).
    pub(crate) ack: Inputs,
    /// Every well-formed directive, in file then source order.
    pub(crate) directives: Vec<DirectiveRecord>,
    /// The ledger when the repository has one with tickets.
    pub(crate) ledger: Option<LedgerState>,
    /// `[invariants]`.
    pub(crate) invariants: InvariantsConfig,
    /// True when `frob.toml` carries a `[tickets]` table, so a ledger is expected.
    pub(crate) tickets_configured: bool,
}

impl FrobInputs {
    /// The inputs of `frob-obligations`, borrowed from these.
    pub(crate) fn obligations(&self) -> ObligationInputs<'_> {
        ObligationInputs {
            root: &self.root,
            graph: &self.ack.graph,
            directives: &self.directives,
            lock: &self.ack.lock,
            ledger: self.ledger.as_ref().map(|l| &l.ledger),
            files: &self.ack.files,
            config: &self.invariants,
        }
    }
}

/// Open the repository's ledger; `None` without a git work tree or without tickets.
fn open_ledger(root: &Path, cfg: LedgerConfig) -> Option<LedgerState> {
    let repo = match gob_git::Repo::discover(root) {
        Ok(r) if r.work_dir().is_some() => r,
        Ok(_) | Err(_) => {
            tracing::info!(root = %root.display(), "no git work tree: ledger rules are skipped");
            return None;
        }
    };
    let ledger = Ledger::open(repo, cfg);
    let tip = ledger
        .ledger_ref()
        .and_then(|name| ledger.repo().rev_parse(&name).map_err(Into::into));
    let tip = match tip {
        Ok(oid) => oid.to_string(),
        Err(err) => {
            tracing::info!(%err, "ledger ref does not resolve: ledger rules are skipped");
            return None;
        }
    };
    match ledger.ticket_ids_at(&tip) {
        Ok(ids) if !ids.is_empty() => {
            tracing::info!(tickets = ids.len(), %tip, "ledger present");
            let tickets = ids.len();
            // frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
            let milestones = frob_pm::rules::membership::milestones(&ledger).map_or_else(
                |err| {
                    tracing::warn!(%err, "milestones unreadable: PM034 not evaluated");
                    0
                },
                |m| m.len(),
            );
            Some(LedgerState {
                ledger,
                tip,
                tickets,
                milestones,
            })
        }
        Ok(_) => {
            tracing::info!(%tip, "ledger holds no tickets: ledger rules are skipped");
            None
        }
        Err(err) => {
            tracing::warn!(%err, "ledger unreadable: ledger rules are skipped");
            None
        }
    }
}

/// Bump when the scan's output for a given text changes; part of the empty-scan cache key.
const SCAN_VERSION: u32 = 1;

/// One scanned file.
struct Scanned {
    directives: Vec<DirectiveRecord>,
    findings: Vec<Finding>,
}

/// Scan `entry` for directives when its text carries the marker.
///
/// A file whose scan found nothing (a stray mention of the marker) is
/// remembered by content digest and skipped next time; directive records are
/// not serializable, so files that do carry directives are rescanned.
fn scan_one(
    root: &Path,
    cache: &Cache,
    entry: &FileEntry,
    file: FileId,
    scanner: &Scanner,
) -> Option<Scanned> {
    let lang = Language::detect(&entry.path)?;
    let key = ArtifactKey {
        content_digest: entry.digest.to_string(),
        producer_identity: format!(
            "frob-check/scan-empty/v{SCAN_VERSION}/{EXTRACTOR_VERSION}/{}",
            grammar_identity(lang)
        ),
    };
    if cache.get_artifact(&key).is_some() {
        return None;
    }
    let text = std::fs::read_to_string(root.join(&entry.path)).ok()?;
    if !text.contains(DIRECTIVE_MARKER) {
        return None;
    }
    let symbols = extract_file(entry, &text);
    let result = scanner.scan_in(file, lang, &text, &symbols);
    if result.directives.is_empty() && result.findings.is_empty() {
        cache.put_artifact(&key, b"empty");
        return None;
    }
    Some(Scanned {
        directives: result.directives,
        findings: result.findings,
    })
}

/// The `frob:doc` directives among `directives`, in the shape `frob-ack` evaluates.
fn doc_directives(directives: &[DirectiveRecord], files: &FileInterner) -> Vec<DocDirective> {
    let mut out = Vec::new();
    for d in directives
        .iter()
        .filter(|d| d.namespace == "frob" && d.verb == "doc")
    {
        let Ok(doc) = Doc::parse_args(&d.args) else {
            tracing::debug!("malformed frob:doc skipped (PARSE001 reports it)");
            continue;
        };
        let Some(path) = files.path(d.span.file) else {
            continue;
        };
        let symbol = match &d.bound {
            Binding::Symbol(s) => s.clone(),
            Binding::File => Symref::file(path),
        };
        out.push(DocDirective {
            file: path.to_owned(),
            span: d.span,
            symbol,
            target: doc.target.0,
        });
    }
    out
}

/// True when `<root>/frob.toml` has a `[tickets]` table (an unreadable file counts as absent).
fn tickets_configured(root: &Path) -> bool {
    std::fs::read_to_string(root.join("frob.toml"))
        .ok()
        .and_then(|t| t.parse::<toml::Table>().ok())
        .is_some_and(|t| t.get("tickets").is_some_and(toml::Value::is_table))
}

/// Collect frob's inputs of one run on top of the walk in `cx`.
///
/// Stage times go to `cx.timing`; graph cache counters to `cx.stats`.
pub(crate) fn collect(
    cx: &mut CollectCx<'_>,
    opts: &CheckOptions,
) -> Result<Collected<Frob>, CheckError> {
    let core = cx.core;
    let (root, entries, files, index) = (&core.root, &core.entries, &core.files, &core.index);
    let started = Instant::now();
    let (graph, built) = build_graph_with_stats(root, entries, cx.cache);
    cx.stats.graph_cached = built.cached;
    cx.stats.graph_extracted = built.extracted;
    cx.timing.push("graph", started.elapsed(), true);

    let started = Instant::now();
    let scanner = Scanner::new(&ScanConfig::default());
    let results: Vec<Scanned> = entries
        .par_iter()
        .filter_map(|e| scan_one(root, cx.cache, e, index.ids[&e.path], &scanner))
        .collect();
    let mut directives = Vec::new();
    let mut scan_findings = Vec::new();
    for s in results {
        directives.extend(s.directives);
        scan_findings.extend(s.findings);
    }
    let lock = LockFile::load(&root.join(file_name(PRODUCT)))?;
    let docs = doc_directives(&directives, files);
    cx.timing.push("directives", started.elapsed(), true);

    let started = Instant::now();
    let ledger_cfg = opts.ledger.clone().unwrap_or_else(|| {
        frob_evidence::workspace::ledger_config(root).unwrap_or_else(|err| {
            tracing::warn!(%err, "ledger config unreadable; using defaults");
            LedgerConfig::default()
        })
    });
    let ledger = open_ledger(root, ledger_cfg);
    cx.timing.push("ledger", started.elapsed(), true);
    let invariants = InvariantsConfig::load(root)?;

    let obligation_paths: BTreeSet<String> = graph
        .records()
        .filter(|r| matches!(r.symref.target(), Target::File))
        .map(|r| r.symref.path().to_owned())
        .chain(
            directives
                .iter()
                .filter_map(|d| files.path(d.span.file).map(str::to_owned)),
        )
        .collect();
    tracing::info!(
        files = entries.len(),
        symbols = graph.node_count(),
        directives = directives.len(),
        "inputs collected"
    );
    let shared = FrobShared {
        ledger_tip: ledger.as_ref().map_or_else(String::new, |l| l.tip.clone()),
        obligation_paths,
        has_ledger: ledger.is_some(),
        file_info: graph
            .files()
            .map(|(p, i)| (p.to_owned(), i.clone()))
            .collect(),
    };
    Ok(Collected {
        shared,
        inputs: FrobInputs {
            root: root.clone(),
            ack: Inputs {
                graph,
                lock,
                docs,
                files: files.clone(),
            },
            directives,
            ledger,
            invariants,
            tickets_configured: tickets_configured(root),
        },
        findings: scan_findings,
    })
}
