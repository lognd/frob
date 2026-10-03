//! The options and results of a land, and the deterministic dry-run plan.

use std::fmt;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use frob_ledger::TicketId;
use frob_ledger::model::Outcome;
use schemars::JsonSchema;
use serde::Serialize;

/// Tuning of the stale-base retry loop `--wait` enables (frob:ticket ~VMHTBE7).
#[derive(Clone)]
pub struct RetryPolicy {
    /// First backoff ceiling; doubles each attempt up to `max`.
    pub backoff_base: Duration,
    /// Largest backoff ceiling.
    pub backoff_max: Duration,
    /// Total retry budget; `--wait` seconds when absent.
    pub budget: Option<Duration>,
    /// Called with the attempt number just before each compare-and-swap; a test seam.
    pub before_attempt: Option<Arc<dyn Fn(u32) + Send + Sync>>,
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self {
            backoff_base: Duration::from_millis(50),
            backoff_max: Duration::from_secs(2),
            budget: None,
            before_attempt: None,
        }
    }
}

impl fmt::Debug for RetryPolicy {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RetryPolicy")
            .field("backoff_base", &self.backoff_base)
            .field("backoff_max", &self.backoff_max)
            .field("budget", &self.budget)
            .field("before_attempt", &self.before_attempt.is_some())
            .finish()
    }
}

/// Options of [`crate::land()`].
#[derive(Debug, Clone)]
pub struct LandOptions {
    /// The ticket (`~handle`, ULID or alias); the ticket leased by the current worktree when absent.
    pub handle: Option<String>,
    /// Print the plan and its digest; change nothing.
    pub dry_run: bool,
    /// Push the base branch to `origin` after advancing it.
    pub push: bool,
    /// Seconds to wait for the land lock, and to retry a stale base, before refusing.
    pub wait_secs: u64,
    /// Keep the worktree and branch after landing.
    pub keep_worktree: bool,
    /// Close without measured evidence, saying why (`--no-evidence --reason`).
    pub no_evidence_reason: Option<String>,
    /// Close without a changelog fragment, saying why (`--no-changelog --reason`).
    pub no_changelog_reason: Option<String>,
    /// The outcome the ticket is closed with.
    pub outcome: Outcome,
    /// Stale-base retry tuning; only used when `wait_secs` is above zero.
    pub retry: RetryPolicy,
}

impl Default for LandOptions {
    fn default() -> Self {
        Self {
            handle: None,
            dry_run: false,
            push: false,
            wait_secs: 0,
            keep_worktree: false,
            no_evidence_reason: None,
            no_changelog_reason: None,
            outcome: Outcome::Done,
            retry: RetryPolicy::default(),
        }
    }
}

/// What a land did, or with `dry_run` what it would do.
#[expect(
    clippy::struct_excessive_bools,
    reason = "each flag is a distinct, serialized fact of the result"
)]
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct LandOutcome {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// True when the ticket was already done and nothing changed.
    pub already: bool,
    /// True when this was a dry run.
    pub dry_run: bool,
    /// Short name of the base branch.
    pub base: String,
    /// The ticket branch.
    pub branch: Option<String>,
    /// The worktree that was (or would be) landed.
    pub worktree: Option<PathBuf>,
    /// The commit the base branch was advanced to.
    pub commit: Option<String>,
    /// How merging the base into the ticket branch went: `up-to-date`, `fast-forward` or `merged`.
    pub base_merge: Option<String>,
    /// True when the base branch was pushed.
    pub pushed: bool,
    /// True when the ticket was closed by this land.
    pub closed: bool,
    /// The outcome the ticket was closed with.
    pub outcome: Option<Outcome>,
    /// True when the worktree and branch were removed.
    pub worktree_removed: bool,
    /// blake3 of ticket id, head oid and base oid (dry run).
    pub digest: Option<String>,
    /// The ordered steps (dry run).
    pub plan: Vec<String>,
    /// Compare-and-swap attempts the publish took (1 unless `--wait` retried a stale base); 0 when nothing was published.
    #[serde(default)]
    pub attempts: u32,
    /// Non-fatal notices.
    pub warnings: Vec<String>,
    /// The reason of the `--no-changelog` exemption this land recorded, when it did.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub changelog_exempt: Option<String>,
}

/// The facts a plan is a pure function of.
#[derive(Debug, Clone)]
pub struct PlanInputs<'a> {
    /// The ticket.
    pub id: TicketId,
    /// Its handle.
    pub handle: &'a str,
    /// Base branch short name.
    pub base: &'a str,
    /// Ticket branch short name.
    pub branch: &'a str,
    /// The worktree path.
    pub worktree: &'a std::path::Path,
    /// True when the base is already contained in the ticket branch.
    pub base_merged: bool,
    /// Outcome to close with.
    pub outcome: Outcome,
    /// Push requested.
    pub push: bool,
    /// Keep the worktree.
    pub keep_worktree: bool,
}

/// The digest of (ticket id, head oid, base oid): the same state always yields the same digest.
pub fn digest(id: TicketId, head: &str, base_oid: &str) -> String {
    let mut h = blake3::Hasher::new();
    h.update(id.to_string().as_bytes());
    h.update(b"\0");
    h.update(head.as_bytes());
    h.update(b"\0");
    h.update(base_oid.as_bytes());
    h.finalize().to_hex().to_string()
}

/// The ordered plan steps for `p`; deterministic in the inputs.
pub fn steps(p: &PlanInputs<'_>) -> Vec<String> {
    let mut v = vec![
        format!(
            "verify {}: leased, worktree clean, check green, evidence guard",
            p.handle
        ),
        if p.base_merged {
            format!("{} already contains {}; no merge needed", p.branch, p.base)
        } else {
            format!("merge {} into {}", p.base, p.branch)
        },
        "take the land lock".to_owned(),
        format!("fast-forward {} to {}", p.base, p.branch),
    ];
    if p.push {
        v.push(format!("push {} to origin", p.base));
    }
    v.push(format!(
        "record the land event and close {} as {}",
        p.handle, p.outcome
    ));
    v.push("release the lease".to_owned());
    v.push(if p.keep_worktree {
        format!("keep worktree {}", p.worktree.display())
    } else {
        format!(
            "remove worktree {} and branch {}",
            p.worktree.display(),
            p.branch
        )
    });
    v
}
