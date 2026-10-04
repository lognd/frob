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
use gob_directives::{
    Binding, Directive, DirectiveRecord, ScanConfig, Scanner, WIRE_VERSION, decode_records,
    encode_records,
};
use gob_languages::{Language, grammar_identity};
use gob_lock::{LockFile, file_name};
use gob_rules::Finding;
use gob_symbols::{EXTRACTOR_VERSION, Symref, Target, build_graph_with_stats, extract_file};
use gob_text::{FileId, FileInterner};
use gob_walk::{FileEntry, Roles};
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

impl LedgerState {
    /// True when the ledger holds any ticket or milestone: the one predicate for ledger-rule applicability.
    pub(crate) fn is_populated(&self) -> bool {
        self.tickets > 0 || self.milestones > 0
    }
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
    /// Walked files the graph build could not read, with reasons (`READ001`).
    pub unreadable: Vec<gob_symbols::SkippedFile>,
    /// Structural file roles: ledger files are data, never examined by the obligation rules.
    pub roles: Roles,
}

/// Everything frob's rules read besides the walk, built once per pass.
pub struct FrobInputs {
    /// Repository root.
    pub(crate) root: std::path::PathBuf,
    /// Graph, lock, `frob:doc` directives and the shared interner (frob-ack's input bundle).
    pub(crate) ack: Inputs,
    /// Every well-formed directive, in file then source order.
    pub(crate) directives: Vec<DirectiveRecord>,
    /// The ledger when the repository has one holding tickets or milestones.
    pub(crate) ledger: Option<LedgerState>,
    /// Why the ledger exists but could not be read; ledger rules then report required Unresolved, never silence.
    pub(crate) ledger_error: Option<String>,
    /// `[invariants]`.
    pub(crate) invariants: InvariantsConfig,
    /// True when `frob.toml` carries a `[tickets]` table, so a ledger is expected.
    pub(crate) tickets_configured: bool,
    /// True when the caller declared the checked ticket exempt from the changelog fragment.
    pub(crate) changelog_exempt: bool,
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

/// Open the repository's ledger.
///
/// `(None, None)` without a git work tree, ledger ref or tickets and milestones;
/// `(None, Some(why))` when the ledger exists but cannot be read, so its rules fail loudly.
// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
fn open_ledger(root: &Path, cfg: LedgerConfig) -> (Option<LedgerState>, Option<String>) {
    let repo = match gob_git::Repo::discover(root) {
        Ok(r) if r.work_dir().is_some() => r,
        Ok(_) | Err(_) => {
            tracing::info!(root = %root.display(), "no git work tree: ledger rules are skipped");
            return (None, None);
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
            return (None, None);
        }
    };
    let tickets = match ledger.ticket_ids_at(&tip) {
        Ok(ids) => ids.len(),
        Err(err) => {
            tracing::warn!(%err, "ledger unreadable: ledger rules report required Unresolved");
            return (None, Some(err.to_string()));
        }
    };
    // frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
    // frob:ticket 01M41DQF8CJG567CJ1AWETTCK4
    let milestones = match frob_pm::rules::membership::milestones(&ledger) {
        Ok(m) => m.len(),
        Err(err) => {
            tracing::warn!(%err, "milestones unreadable: ledger rules report required Unresolved");
            return (None, Some(format!("milestones unreadable: {err}")));
        }
    };
    let state = LedgerState {
        ledger,
        tip,
        tickets,
        milestones,
    };
    if state.is_populated() {
        tracing::info!(tickets, milestones, tip = %state.tip, "ledger present");
        (Some(state), None)
    } else {
        tracing::info!(tip = %state.tip, "ledger holds no tickets or milestones: ledger rules are skipped");
        (None, None)
    }
}

/// Bump when the scan's output for a given text changes; part of the scan cache key.
const SCAN_VERSION: u32 = 2;

/// One scanned file.
struct Scanned {
    directives: Vec<DirectiveRecord>,
    findings: Vec<Finding>,
}

// frob:ticket 01M41ZSWGC86TY3K0NSA8AMNGF
/// What [`scan_one`] did for one file.
struct ScanOutcome {
    /// The file's directives and findings, `None` when it has neither.
    scanned: Option<Scanned>,
    /// True when the file was read and scanned, false when its records came from the cache.
    fresh: bool,
}

// frob:ticket 01M41ZSWGC86TY3K0NSA8AMNGF
/// Scan `entry` for directives, serving unchanged files from the artifact cache.
///
/// Every file of a known language is cached by content digest, engine and
/// grammar: a file without the marker or with a clean scan stores its (possibly
/// empty) directive records and is not read next time. A file whose scan
/// raised findings is rescanned each run, as findings are not serialized.
fn scan_one(
    root: &Path,
    cache: &Cache,
    entry: &FileEntry,
    file: FileId,
    scanner: &Scanner,
    roles: &Roles,
) -> Option<ScanOutcome> {
    if !roles.role(&entry.path).scans_directives() {
        return None;
    }
    let lang = Language::detect(&entry.path)?;
    let key = ArtifactKey {
        content_digest: entry.digest.to_string(),
        producer_identity: format!(
            "frob-check/scan/v{SCAN_VERSION}/{WIRE_VERSION}/{EXTRACTOR_VERSION}/{}/{}",
            cache.engine(),
            grammar_identity(lang)
        ),
    };
    if let Some(bytes) = cache.get_artifact(&key)
        && let Some(directives) = decode_records(&bytes, file)
    {
        tracing::debug!(
            path = %entry.path,
            directives = directives.len(),
            "directive scan served from cache"
        );
        let found = (!directives.is_empty()).then_some(Scanned {
            directives,
            findings: Vec::new(),
        });
        return Some(ScanOutcome {
            scanned: found,
            fresh: false,
        });
    }
    let fresh = |scanned| {
        Some(ScanOutcome {
            scanned,
            fresh: true,
        })
    };
    let Ok(text) = std::fs::read_to_string(root.join(&entry.path)) else {
        return fresh(None);
    };
    let (directives, findings) = if text.contains(DIRECTIVE_MARKER) {
        let symbols = extract_file(entry, &text);
        let result = scanner.scan_in(file, lang, &text, &symbols);
        (result.directives, result.findings)
    } else {
        (Vec::new(), Vec::new())
    };
    if findings.is_empty()
        && let Some(bytes) = encode_records(&directives)
    {
        cache.put_artifact(&key, &bytes);
    }
    if directives.is_empty() && findings.is_empty() {
        return fresh(None);
    }
    fresh(Some(Scanned {
        directives,
        findings,
    }))
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
    // frob:ticket 01M43KP0RXKB1DJA8KGJTV288R
    let ledger_cfg = opts.ledger.clone().unwrap_or_else(|| {
        frob_evidence::workspace::ledger_config(root).unwrap_or_else(|err| {
            tracing::warn!(%err, "ledger config unreadable; using defaults");
            LedgerConfig::default()
        })
    });
    let roles = Roles::new(&ledger_cfg.dir);
    let outcomes: Vec<ScanOutcome> = entries
        .par_iter()
        .filter_map(|e| scan_one(root, cx.cache, e, index.ids[&e.path], &scanner, &roles))
        .collect();
    let mut directives = Vec::new();
    let mut scan_findings = Vec::new();
    for o in &outcomes {
        if o.fresh {
            cx.stats.directives_scanned += 1;
        } else {
            cx.stats.directives_cached += 1;
        }
    }
    for s in outcomes.into_iter().filter_map(|o| o.scanned) {
        directives.extend(s.directives);
        scan_findings.extend(s.findings);
    }
    tracing::info!(
        scanned = cx.stats.directives_scanned,
        cached = cx.stats.directives_cached,
        "directive scan done"
    );
    let lock = LockFile::load(&root.join(file_name(PRODUCT)))?;
    let docs = doc_directives(&directives, files);
    cx.timing.push("directives", started.elapsed(), true);

    let started = Instant::now();
    let (ledger, ledger_error) = open_ledger(root, ledger_cfg);
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
        unreadable: built.unreadable,
        roles,
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
            ledger_error,
            invariants,
            tickets_configured: tickets_configured(root),
            changelog_exempt: opts.changelog_exempt,
        },
        findings: scan_findings,
    })
}
