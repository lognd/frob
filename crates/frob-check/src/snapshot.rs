//! Input collection, done once per run: walk, graph, directives, lock and ledger.

use std::collections::{BTreeSet, HashMap, HashSet};
use std::path::Path;
use std::time::Instant;

use frob_ack::{DocDirective, Inputs};
use frob_ledger::{Ledger, LedgerConfig};
use frob_obligations::{InvariantsConfig, ObligationInputs};
use gob_cache::{ArtifactKey, Cache};
use gob_directives::frob::Doc;
use gob_directives::{Binding, Directive, DirectiveRecord, ScanConfig, Scanner};
use gob_languages::{Language, grammar_identity};
use gob_lock::{LockFile, file_name};
use gob_rules::Finding;
use gob_symbols::{EXTRACTOR_VERSION, Symref, Target, build_graph_with_stats, extract_file};
use gob_text::{FileId, FileInterner};
use gob_walk::{FileEntry, WalkConfig, walk};
use rayon::prelude::*;

use crate::config::CheckTable;
use crate::error::CheckError;
use crate::options::CheckOptions;
use crate::report::{Stats, Timing};

/// The product whose `frob.lock` and `.frob/` the check reads.
pub(crate) const PRODUCT: &str = "frob";

/// Substring that makes a file worth scanning for directives (cheap prefilter).
const DIRECTIVE_MARKER: &str = "frob:";

/// Read-only, thread-safe facts about the walked files.
pub(crate) struct FileIndex {
    /// Interned id per repo-relative path.
    pub ids: HashMap<String, FileId>,
    /// Hex content digest per path.
    pub digests: HashMap<String, String>,
    /// Every ancestor directory of a walked file (links to directories resolve).
    pub dirs: HashSet<String>,
}

/// The ledger and the commit it was read at.
pub(crate) struct LedgerState {
    /// The open ledger.
    pub ledger: Ledger,
    /// Ledger tip commit, hex; the side-input digest of ledger-reading rules.
    pub tip: String,
}

/// Everything the rules read, built once.
pub(crate) struct Snapshot {
    /// Repository root.
    pub root: std::path::PathBuf,
    /// Walked files, sorted by path.
    pub entries: Vec<FileEntry>,
    /// Path lookups.
    pub index: FileIndex,
    /// Graph, lock, `frob:doc` directives and the shared interner (frob-ack's input bundle).
    pub ack: Inputs,
    /// Every well-formed directive, in file then source order.
    pub directives: Vec<DirectiveRecord>,
    /// PARSE001, DSL001 and DSL002 findings of the scan.
    pub scan_findings: Vec<Finding>,
    /// The ledger when the repository has one with tickets.
    pub ledger: Option<LedgerState>,
    /// `[invariants]`.
    pub invariants: InvariantsConfig,
    /// Files the obligation rules evaluate: graph file nodes plus files holding a directive.
    pub obligation_paths: BTreeSet<String>,
}

impl Snapshot {
    /// The inputs of `frob-obligations`, borrowed from this snapshot.
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

    /// The ledger tip, or the empty string without a ledger.
    pub(crate) fn ledger_tip(&self) -> &str {
        self.ledger.as_ref().map_or("", |l| l.tip.as_str())
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
            Some(LedgerState { ledger, tip })
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

/// Collect every input of one run.
///
/// Stage times go to `timing`; graph cache counters to `stats`.
pub(crate) fn collect(
    root: &Path,
    table: &CheckTable,
    cache: &Cache,
    opts: &CheckOptions,
    timing: &mut Timing,
    stats: &mut Stats,
) -> Result<Snapshot, CheckError> {
    let started = Instant::now();
    let mut exclude = vec!["/.frob/".to_owned(), "/target/".to_owned()];
    exclude.extend(table.exclude.iter().cloned());
    let walked = walk(
        root,
        &WalkConfig {
            exclude,
            size_cap: table.size_cap,
            ..WalkConfig::default()
        },
    )?;
    for big in &walked.oversized {
        tracing::info!(path = %big.path, size = big.size, "file over size_cap skipped");
    }
    let mut entries = walked.files;
    entries.sort_by(|a, b| a.path.cmp(&b.path));
    let mut files = FileInterner::new();
    let mut index = FileIndex {
        ids: HashMap::with_capacity(entries.len()),
        digests: HashMap::with_capacity(entries.len()),
        dirs: HashSet::new(),
    };
    for e in &entries {
        index.ids.insert(e.path.clone(), files.intern(&e.path));
        index.digests.insert(e.path.clone(), e.digest.to_string());
        let mut dir = e.path.as_str();
        while let Some((parent, _)) = dir.rsplit_once('/') {
            if !index.dirs.insert(parent.to_owned()) {
                break;
            }
            dir = parent;
        }
    }
    stats.files = entries.len();
    timing.push("walk", started.elapsed(), true);

    let started = Instant::now();
    let (graph, built) = build_graph_with_stats(root, &entries, cache);
    stats.graph_cached = built.cached;
    stats.graph_extracted = built.extracted;
    timing.push("graph", started.elapsed(), true);

    let started = Instant::now();
    let scanner = Scanner::new(&ScanConfig::default());
    let results: Vec<Scanned> = entries
        .par_iter()
        .filter_map(|e| scan_one(root, cache, e, index.ids[&e.path], &scanner))
        .collect();
    let mut directives = Vec::new();
    let mut scan_findings = Vec::new();
    for s in results {
        directives.extend(s.directives);
        scan_findings.extend(s.findings);
    }
    let lock = LockFile::load(&root.join(file_name(PRODUCT)))?;
    let docs = doc_directives(&directives, &files);
    timing.push("directives", started.elapsed(), true);

    let started = Instant::now();
    let ledger_cfg = opts.ledger.clone().unwrap_or_else(|| {
        frob_evidence::workspace::ledger_config(root).unwrap_or_else(|err| {
            tracing::warn!(%err, "ledger config unreadable; using defaults");
            LedgerConfig::default()
        })
    });
    let ledger = open_ledger(root, ledger_cfg);
    timing.push("ledger", started.elapsed(), true);
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
    Ok(Snapshot {
        root: root.to_path_buf(),
        entries,
        index,
        ack: Inputs {
            graph,
            lock,
            docs,
            files,
        },
        directives,
        scan_findings,
        ledger,
        invariants,
        obligation_paths,
    })
}
