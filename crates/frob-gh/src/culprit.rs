//! Culprit finding: which land commits sit between the last green CI run and the first red one.
//!
//! Pure over data: [`Client::workflow_runs`] reads the runs, the caller supplies the first-parent
//! history (newest first), and [`find_culprit`] names the `tickets(land)` commits in the range
//! plus a [`FixTicket`] spec whose idempotency key comes from the first-red sha, so a repeat
//! finding files nothing new (~WFY48QC, epic ~HWZXYC7).

// frob:ticket 01M4GRXFQYZRDJ2TP68WFY48QC
use serde::Deserialize;

use crate::{Client, Error, Pause, Transport};

/// Subject prefix that marks a land commit on the base branch.
pub const LAND_PREFIX: &str = "tickets(land)";

/// Label carried by the fix ticket so lands can refuse while it is open.
pub const BLOCKS_LANDS_LABEL: &str = "blocks-lands";

/// How one workflow run ended, reduced to what culprit finding needs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    /// Completed successfully.
    Green,
    /// Completed with failure, timeout or startup failure.
    Red,
    /// Not finished, cancelled or skipped: says nothing either way.
    Unknown,
}

/// One workflow run of a commit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunRecord {
    /// The commit the run tested.
    pub sha: String,
    /// The run's verdict.
    pub verdict: Verdict,
}

#[derive(Deserialize)]
struct RunsPage {
    workflow_runs: Vec<RawRun>,
}

#[derive(Deserialize)]
struct RawRun {
    head_sha: String,
    status: Option<String>,
    conclusion: Option<String>,
}

impl RawRun {
    fn verdict(&self) -> Verdict {
        if self.status.as_deref() != Some("completed") {
            return Verdict::Unknown;
        }
        match self.conclusion.as_deref() {
            Some("success") => Verdict::Green,
            Some("failure" | "timed_out" | "startup_failure") => Verdict::Red,
            _ => Verdict::Unknown,
        }
    }
}

impl<T: Transport, P: Pause> Client<T, P> {
    /// The latest (up to 100) workflow runs of `branch`, in GitHub's newest-first order.
    ///
    /// # Errors
    /// Any [`Error`] from the request, or [`Error::Json`] on an unexpected body.
    pub async fn workflow_runs(
        &self,
        owner: &str,
        repo: &str,
        branch: &str,
    ) -> Result<Vec<RunRecord>, Error> {
        let path = format!("/repos/{owner}/{repo}/actions/runs?branch={branch}&per_page=100");
        let page: RunsPage = self.get(&path).await?.json()?;
        let runs: Vec<RunRecord> = page
            .workflow_runs
            .iter()
            .map(|r| RunRecord {
                sha: r.head_sha.clone(),
                verdict: r.verdict(),
            })
            .collect();
        tracing::debug!(owner, repo, branch, runs = runs.len(), "read workflow runs");
        Ok(runs)
    }
}

/// One first-parent commit of the base branch.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Commit {
    /// Full or abbreviated sha.
    pub sha: String,
    /// First line of the message.
    pub subject: String,
}

/// The ticket to file for a red base; filing is the caller's, idempotent on `idempotency_key`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FixTicket {
    /// Same for every finding of the same first-red commit.
    pub idempotency_key: String,
    /// Ticket title naming the range.
    pub title: String,
    /// Ticket body listing the suspect land commits.
    pub body: String,
    /// Labels, including [`BLOCKS_LANDS_LABEL`].
    pub labels: Vec<String>,
}

/// A located culprit range.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Culprit {
    /// Newest commit with a green verdict before the red streak, if the history reaches one.
    pub last_green: Option<String>,
    /// Oldest commit of the current red streak.
    pub first_red: String,
    /// The `tickets(land)` commits after `last_green` up to `first_red`, oldest first.
    pub lands: Vec<Commit>,
    /// The fix ticket to file.
    pub fix: FixTicket,
}

/// Why no culprit could be named.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum CulpritError {
    /// The newest decided commit is green (or there is none): nothing to blame.
    #[error("the base is not red")]
    NotRed,
    /// A decided run's commit is not in the supplied history.
    #[error("run commit {0} is not in the supplied history")]
    NotInHistory(String),
}

fn same(a: &str, b: &str) -> bool {
    a.starts_with(b) || b.starts_with(a)
}

/// Per-commit verdict: red if any run is red, green if all decided runs are green, else unknown.
fn commit_verdict(runs: &[RunRecord], sha: &str) -> Verdict {
    let mine: Vec<Verdict> = runs
        .iter()
        .filter(|r| same(&r.sha, sha))
        .map(|r| r.verdict)
        .collect();
    if mine.contains(&Verdict::Red) {
        Verdict::Red
    } else if !mine.is_empty() && mine.iter().all(|v| *v == Verdict::Green) {
        Verdict::Green
    } else {
        Verdict::Unknown
    }
}

/// Name the land commits between the last green and the first red of the newest red streak.
///
/// `history` is newest first. Commits with an unknown verdict are skipped, so a pending run does
/// not hide a streak; the range then spans them (they stay suspects).
///
/// # Errors
/// [`CulpritError::NotRed`] when the newest decided commit is not red;
/// [`CulpritError::NotInHistory`] when a run's commit is missing from `history`.
pub fn find_culprit(runs: &[RunRecord], history: &[Commit]) -> Result<Culprit, CulpritError> {
    if let Some(r) = runs
        .iter()
        .find(|r| r.verdict != Verdict::Unknown && !history.iter().any(|c| same(&c.sha, &r.sha)))
    {
        return Err(CulpritError::NotInHistory(r.sha.clone()));
    }
    let decided: Vec<(usize, Verdict)> = history
        .iter()
        .enumerate()
        .map(|(i, c)| (i, commit_verdict(runs, &c.sha)))
        .filter(|(_, v)| *v != Verdict::Unknown)
        .collect();
    let Some(&(_, Verdict::Red)) = decided.first() else {
        return Err(CulpritError::NotRed);
    };
    let green_at = decided
        .iter()
        .find(|(_, v)| *v == Verdict::Green)
        .map(|(i, _)| *i);
    let streak_end = decided
        .iter()
        .take_while(|(i, _)| green_at.is_none_or(|g| *i < g))
        .last()
        .map_or(0, |(i, _)| *i);
    let first_red = history[streak_end].sha.clone();
    let last_green = green_at.map(|g| history[g].sha.clone());
    let stop = green_at.unwrap_or(history.len());
    let lands: Vec<Commit> = history[streak_end..stop]
        .iter()
        .filter(|c| c.subject.starts_with(LAND_PREFIX))
        .rev()
        .cloned()
        .collect();
    tracing::info!(%first_red, ?last_green, lands = lands.len(), "culprit range found");
    let short = |s: &str| s[..s.len().min(9)].to_owned();
    let names = lands
        .iter()
        .map(|c| format!("- {} {}", short(&c.sha), c.subject))
        .collect::<Vec<_>>()
        .join("\n");
    let fix = FixTicket {
        idempotency_key: format!("culprit-{first_red}"),
        title: format!(
            "Base CI red since {}: fix or revert the land range after {}",
            short(&first_red),
            last_green
                .as_deref()
                .map_or("(no green run)".to_owned(), short),
        ),
        body: format!(
            "Base CI is red. Land commits between the last green run and the first red run:\n{names}\n"
        ),
        labels: vec![BLOCKS_LANDS_LABEL.to_owned()],
    };
    Ok(Culprit {
        last_green,
        first_red,
        lands,
        fix,
    })
}
