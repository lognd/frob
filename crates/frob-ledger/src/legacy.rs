//! Legacy-derive ledger rules (`TICK007` to `TICK010`) that the declared rule shape cannot yet express.

use gob_rules::{Rule, RuleId};

/// A ledger commit without the reindex trailer renamed or deleted a ticket file, or touched an event file it did not add.
///
/// Only a reindex commit (trailer `Frob-Reindex`) may move a ticket file; ordinary commits add events and edit
/// frontmatter. Scrub, migrate, init and reconcile commits are exempt by subject, as is a commit that exactly undoes an
/// earlier ledger commit (a revert) or carries a `Frob-Allow-Move: <reason>` trailer. Fix the move by reindexing instead.
// frob:ticket 01M3ZX86W1P62F80ZNR17Q0SQ9
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK008",
    slug = "move-outside-reindex",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Tick008;

/// A ticket file on the tip of the ticket branch is not at its computed path.
///
/// Every ticket file sits at `<top-epic-slug>/<slug>.md` (or `_unfiled/`). A parent or title change that was left
/// to CI, a hand rename or a stale checkout leaves files elsewhere. Run `frob ticket reindex` to move them.
// frob:ticket 01M3ZX86ZX0SCN2FHTDBQF97FD
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK009",
    slug = "misfiled-ticket",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Tick009;

/// A reindex commit is not what the pure reindex of its parent tree produces.
///
/// Replaying the reindex in memory on the parent commit's tree with the frob version named in the commit's
/// `Frob-Reindex` trailer must give the commit's own tree; a difference means a hand edit rode in on a reindex
/// commit. When that version is not the one running, the result is Unresolved with reason `generator-version`.
// frob:ticket 01M3ZX86R5V67MT726K3X7KVWM
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK007",
    slug = "reindex-not-pure",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Tick007;

/// A `.github/` tree on the ticket branch is not exactly the generated nudge workflow.
///
/// The only `.github/` file the ticket branch may carry is the nudge workflow, and its bytes must equal what
/// `frob` generates. Any other file under `.github/`, or an edited nudge, is an Error: a workflow on the ticket
/// branch runs with the repository token. Delete the file, or regenerate the nudge.
// frob:ticket 01M4052VK08NTRJS6HZZ9B82RZ
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TICK010",
    slug = "ledger-branch-workflow",
    family = "TICK",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Tick010;

/// Parse the rule id the derive already validated.
pub(crate) fn id_of<R: Rule>(rule: &R) -> RuleId {
    rule.meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}
