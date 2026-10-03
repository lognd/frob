//! `REL003`: a changelog fragment is missing for the ticket under check, or does not validate.
//!
//! Fragments are `changelog.d/<ULID>.<type>.md` (`documentation.md` section 6). [`evaluate`]
//! runs repository-wide and reports every fragment the compile's own validator rejects, so a
//! bad one is seen before `frob release changelog` trips over it. [`missing`] is the ticket
//! half: under `check --ticket` it names the checked ticket when it has no fragment file yet.
//! The `changelog_fragment` close guard (`frob-evidence`) runs the same validator.

use std::path::Path;

use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::FragmentError;
use crate::fragment::{TicketResolver, files_of, read_all};

// frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
/// A changelog fragment that is missing for the checked ticket or that fails validation.
///
/// A fragment is `changelog.d/<ULID>.<type>.md` with a type of added, changed, fixed,
/// removed, deprecated or security, a ULID that names a ticket in the ledger, and a non-empty
/// ASCII body of one or two user-facing sentences, optionally prefixed with a product
/// (`frob:`). Repository-wide the rule fires for each fragment that does not validate: an
/// unknown type, a name that is not a ULID, a ULID with no ticket, an empty or non-ASCII
/// body, or a product prefix that is a near miss of a real product. Under `check --ticket`
/// it also fires when the checked ticket is not yet done and has no fragment file at all.
/// It is not applicable when `changelog_fragment` is not in `[pm] done_requires` and the
/// repository has no `changelog.d` directory.
///
/// ## Remedy
///
/// For a missing fragment run `frob ticket fragment TICKET` in the ticket's worktree: it
/// writes `changelog.d/<ULID>.<type>.md` from the title (`--type` and `--sentence` set them),
/// validated by the same code; edit the sentence and commit it, or, audited, close the ticket with
/// `--no-changelog --reason TEXT`. For an invalid fragment,
/// fix what the message names (rename the file, reword the body) or replace it with
/// `frob ticket fragment TICKET --force`. A change with no user-visible effect (a design
/// document, an internal refactor) is closed with `--no-changelog --reason TEXT` instead; the
/// exemption is a `changelog-exempt` event, audited, and a ticket that has one is not reported.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "REL003",
    slug = "changelog-fragment-required",
    family = "REL",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Rel003;

/// What [`evaluate`] found.
#[derive(Debug, Clone, Default)]
pub struct Evaluation {
    /// `REL003` findings: one Error per invalid fragment.
    pub findings: Vec<Finding>,
    /// Fragment files examined.
    pub subjects: usize,
}

fn rule_id() -> RuleId {
    Rel003
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// The finding for one fragment error, keyed by the file.
fn invalid(err: &FragmentError) -> Finding {
    tracing::debug!(file = err.file(), %err, "REL003: invalid fragment");
    Finding::new(
        rule_id(),
        Severity::Error,
        None,
        format!("REL003: {err}; fix it, or replace it with `frob ticket fragment TICKET --force`"),
        &format!("invalid:{}", err.file()),
    )
}

/// Report every fragment under `<root>/changelog.d` that the compile's validator rejects.
///
/// A missing directory is an empty evaluation. `resolver` decides whether a ULID is a ticket.
#[must_use]
pub fn evaluate(root: &Path, resolver: &dyn TicketResolver) -> Evaluation {
    let dir = root.join("changelog.d");
    let subjects = std::fs::read_dir(&dir).map_or(0, |rd| {
        rd.filter_map(Result::ok)
            .filter(|e| e.path().is_file() && e.file_name() != ".gitkeep")
            .count()
    });
    let findings = read_all(&dir, resolver)
        .err()
        .map(|errs| errs.iter().map(invalid).collect())
        .unwrap_or_default();
    let out = Evaluation { findings, subjects };
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "REL003 evaluated"
    );
    out
}

/// The finding for ticket `handle` (ULID `ulid`) when it has no fragment file, else `None`.
///
/// Any `<ulid>.*.md` counts as present here, valid or not: an invalid one is reported by
/// [`evaluate`] with its own message, so the ticket is not blamed twice.
#[must_use]
pub fn missing(root: &Path, ulid: &str, handle: &str) -> Option<Finding> {
    if !files_of(&root.join("changelog.d"), ulid).is_empty() {
        tracing::debug!(handle, "REL003: ticket has a fragment file");
        return None;
    }
    tracing::debug!(handle, "REL003: ticket has no fragment");
    Some(Finding::new(
        rule_id(),
        Severity::Error,
        None,
        format!(
            "REL003: ticket {handle} has no changelog fragment: changelog.d/{ulid}.<type>.md does not exist; run `frob ticket fragment {handle}` in the ticket's worktree, edit the sentence and commit it; or, if the change has no user-visible effect, close with `--no-changelog --reason <why>`"
        ),
        &format!("missing:{ulid}"),
    ))
}

/// Why the rule does not apply: fragments are not required and there is no `changelog.d` to judge.
#[must_use]
pub fn not_applicable(root: &Path, fragment_required: bool) -> Option<String> {
    if fragment_required || root.join("changelog.d").is_dir() {
        return None;
    }
    Some(
        "changelog_fragment is not in [pm] done_requires and the repository has no changelog.d directory"
            .to_owned(),
    )
}
