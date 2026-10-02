//! Accounting rules of frob: the COV, DOC, REF and INV subsets, the to-do rules
//! and exception handling (design: `rules.md` sections 2 and 4, `exceptions.md`
//! sections 1, 2 and 6, `code-model.md` section 6).
//!
//! # Rules
//!
//! | Rule | Severity | Scope | Fires when |
//! |---|---|---|---|
//! | `COV001` | Warn | repo | a public function or method has no test reaching it |
//! | `COV003` | Error | alias | never emitted, see below |
//! | `TODO001` | Error | file | a comment carries a bare upper-case work marker |
//! | `TODO002` | Warn | repo | a `frob:todo` names a done or dropped ticket |
//! | `DOC001` | Warn | file | a public Rust item has no doc comment |
//! | `DOC002` | Error | file | a markdown link points at a missing path or heading |
//! | `REF001` | Error | file | a `frob:ticket` names no ticket of the ledger |
//! | `INV001` | Warn | repo | `invariants/<slug>.md` has no `frob:invariant <slug>` in code |
//! | `INV002` | Error | repo | an import matches `forbid_imports` of [`InvariantsConfig`] |
//! | `EXC001` | Error | repo | an accept or defer carries a rejected reason |
//! | `EXC003` | Error | repo | a defer names a done or dropped ticket |
//! | `EXC005` | Warn | repo | an accept is unattested or its symbol changed since `frob ack` |
//! | `EXC007` | Error | repo | a defer names a ticket that does not exist |
//!
//! The EXC numbers follow the milestone-1 ticket (D36), not the stale and
//! reattest numbering of the exceptions design table.
//!
//! # Per-file versus repo-level
//!
//! [`evaluate_file`] runs the per-file rules (`TODO001`, `DOC001`, `DOC002`,
//! `REF001`) over one file's text; their result depends on that file alone
//! except where noted, so `frob check` may cache it by file digest.
//! `REF001` reads the ledger and `DOC002` reads the link targets on disk, so
//! those two must also fold the ledger tip and the target digests into the
//! key. [`evaluate_repo`] runs the repo-level rules (`COV001`, `TODO002`,
//! `INV001`, `INV002`) over the whole graph; [`apply_exceptions`] then
//! suppresses findings and raises the `EXC*` findings. [`evaluate`] does all
//! three. Files evaluated are the graph's file nodes (Rust and markdown) plus
//! any file holding a directive (TOML among them).
//!
//! # COV003 and TEST001
//!
//! A `frob:tests` directive naming a missing test is one problem and gets one
//! finding. The owner is `frob-tests`, as `TEST001`
//! ([`frob_tests::test001`]). `COV003` stays declared as an alias
//! ([`COV003_ALIAS_OF`]) so references to the id resolve, but this crate never
//! emits it: the registry has no duplicate finding for one cause.
//!
//! # Exceptions
//!
//! `frob:accept <RULE> because="..."` and `frob:defer <RULE> because="..."
//! ticket=<ulid>` suppress findings of that rule whose span lies inside the
//! bound symbol (the whole file when bound to the file). A suppressed finding
//! is returned in [`Evaluation::suppressed`] with its [`gob_rules::Exception`],
//! never dropped. An exception stays in force even when it is itself flagged
//! (`EXC001`, `EXC003`, `EXC005`, `EXC007`), so the gate fails on the
//! exception, once. The `until` key is not evaluated at milestone 1.

mod collect;
mod comments;
mod config;
mod cov;
mod doc;
mod exc;
mod inv;
mod refs;
mod rules;
mod tickets;
mod todo;
mod util;

use std::collections::{BTreeSet, HashMap};
use std::path::Path;

use frob_ledger::Ledger;
use gob_directives::DirectiveRecord;
use gob_lock::LockFile;
use gob_rules::{Exception, Finding};
use gob_symbols::{SymbolGraph, Target};
use gob_text::{FileId, FileInterner};

pub use collect::{CollectError, Collected, collect};
pub use config::{ForbidImport, InvariantsConfig};
pub use gob_rules::Resolved;
pub use rules::{
    Cov001, Cov003, Doc001, Doc002, Exc001, Exc003, Exc005, Exc007, Inv001, Inv002, Ref001,
    Todo001, Todo002,
};

use tickets::Tickets;

/// The rule that owns the finding `COV003` would have produced.
pub const COV003_ALIAS_OF: &str = "TEST001";

/// Everything the rules read, borrowed from the caller's pipeline.
#[derive(Clone, Copy)]
pub struct ObligationInputs<'a> {
    /// Repository root; file text and link targets are read from here.
    pub root: &'a Path,
    /// The symbol graph.
    pub graph: &'a SymbolGraph,
    /// Every well-formed directive of every file.
    pub directives: &'a [DirectiveRecord],
    /// The current `frob.lock`.
    pub lock: &'a LockFile,
    /// The ticket ledger; without one the ticket-dependent rules stay silent.
    pub ledger: Option<&'a Ledger>,
    /// Resolves the `FileId`s inside the directive spans.
    pub files: &'a FileInterner,
    /// The `[invariants]` table.
    pub config: &'a InvariantsConfig,
}

/// The outcome of a full evaluation.
#[derive(Debug, Clone)]
pub struct Evaluation {
    /// Findings left standing, including the `EXC*` findings, sorted by file and offset.
    pub findings: Vec<Finding>,
    /// Findings an exception suppressed, each with that exception.
    pub suppressed: Vec<(Finding, Exception)>,
    /// The caller's interner extended with every file a finding points into.
    pub files: FileInterner,
}

/// Lines of `findings` in file then offset order; spanless findings last.
fn sort_findings(findings: &mut [Finding], files: &FileInterner) {
    findings.sort_by_cached_key(|f| {
        (
            f.span.is_none(),
            f.span.and_then(|s| files.path(s.file)).map(str::to_owned),
            f.span.map(|s| u32::from(s.range.start())),
            f.rule.clone(),
        )
    });
}

/// The directives written in `path`, in source order.
fn directives_of<'a>(inputs: &ObligationInputs<'a>, path: &str) -> Vec<&'a DirectiveRecord> {
    inputs
        .directives
        .iter()
        .filter(|d| inputs.files.path(d.span.file) == Some(path))
        .collect()
}

/// Per-file rules over `text` with the file's own `directives`.
fn file_rules(
    inputs: &ObligationInputs<'_>,
    tickets: &Tickets<'_>,
    file: FileId,
    path: &str,
    text: &str,
    directives: &[&DirectiveRecord],
) -> Vec<Finding> {
    let mut out = todo::todo001(file, path, text, directives);
    out.extend(doc::doc001(inputs.graph, file, path, text));
    out.extend(doc::doc002(inputs.root, file, path, text));
    out.extend(refs::ref001(directives, tickets));
    out
}

/// The per-file rules (`TODO001`, `DOC001`, `DOC002`, `REF001`) over one file.
///
/// `file` is the id of `path` in the caller's interner and `text` its content.
/// Findings are raw: exceptions are applied by [`apply_exceptions`].
pub fn evaluate_file(
    inputs: &ObligationInputs<'_>,
    file: FileId,
    path: &str,
    text: &str,
) -> Vec<Finding> {
    let tickets = Tickets::new(inputs.ledger);
    let directives = directives_of(inputs, path);
    file_rules(inputs, &tickets, file, path, text, &directives)
}

/// The repo-level rules (`COV001`, `TODO002`, `INV001`, `INV002`); new files are interned into `files`.
///
/// Findings are raw: exceptions are applied by [`apply_exceptions`].
pub fn evaluate_repo(inputs: &ObligationInputs<'_>, files: &mut FileInterner) -> Vec<Finding> {
    let tickets = Tickets::new(inputs.ledger);
    let mut out = cov::cov001(inputs.root, inputs.graph, inputs.directives, files);
    out.extend(todo::todo002(inputs.directives, &tickets));
    out.extend(inv::inv001(inputs.graph, inputs.directives, files));
    out.extend(inv::inv002(inputs.root, inputs.graph, inputs.config, files));
    out
}

/// Suppress the findings of `raw` that an accept or defer covers and add the `EXC*` findings.
///
/// `raw` may hold findings of any product's rules: an exception matches by
/// rule id and span, so `frob check` passes the union of every rule's output.
/// `files` must resolve every span in `raw` and in the directives.
pub fn apply_exceptions(
    inputs: &ObligationInputs<'_>,
    files: &FileInterner,
    raw: Vec<Finding>,
) -> Resolved {
    let tickets = Tickets::new(inputs.ledger);
    let mut resolved = exc::resolve(
        inputs.graph,
        inputs.lock,
        inputs.directives,
        files,
        &tickets,
        raw,
    );
    sort_findings(&mut resolved.findings, files);
    resolved
}

/// Evaluate every rule of this crate over the repository and apply exceptions.
pub fn evaluate(inputs: &ObligationInputs<'_>) -> Evaluation {
    let mut files = inputs.files.clone();
    let tickets = Tickets::new(inputs.ledger);
    if inputs.ledger.is_none() {
        tracing::info!("no ledger: REF001, TODO002, EXC003 and EXC007 are not evaluated");
    }
    let mut by_path: HashMap<&str, Vec<&DirectiveRecord>> = HashMap::new();
    for d in inputs.directives {
        if let Some(p) = inputs.files.path(d.span.file) {
            by_path.entry(p).or_default().push(d);
        }
    }
    let paths: BTreeSet<&str> = inputs
        .graph
        .records()
        .filter(|r| matches!(r.symref.target(), Target::File))
        .map(|r| r.symref.path())
        .chain(by_path.keys().copied())
        .collect();
    let mut raw = Vec::new();
    for path in paths {
        let Ok(text) = std::fs::read_to_string(inputs.root.join(path)) else {
            tracing::warn!(path, "unreadable file skipped by per-file rules");
            continue;
        };
        let file = files.intern(path);
        let directives = by_path.get(path).map_or(&[][..], Vec::as_slice);
        raw.extend(file_rules(inputs, &tickets, file, path, &text, directives));
    }
    raw.extend(evaluate_repo(inputs, &mut files));
    let Resolved {
        mut findings,
        suppressed,
    } = exc::resolve(
        inputs.graph,
        inputs.lock,
        inputs.directives,
        &files,
        &tickets,
        raw,
    );
    sort_findings(&mut findings, &files);
    tracing::info!(
        findings = findings.len(),
        suppressed = suppressed.len(),
        "obligations evaluated"
    );
    Evaluation {
        findings,
        suppressed,
        files,
    }
}
