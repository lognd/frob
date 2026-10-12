//! Reading workflow runs over HTTPS; the culprit logic itself lives in `frob_release::culprit`.

// frob:ticket 01M4GRXFQYZRDJ2TP68WFY48QC
use serde::Deserialize;

use crate::{Client, Error, Pause, Transport};

pub use frob_release::culprit::{
    BLOCKS_LANDS_LABEL, Commit, Culprit, CulpritError, FixTicket, LAND_PREFIX, RunRecord, Verdict,
    find_culprit,
};

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
        Verdict::from_run(self.status.as_deref(), self.conclusion.as_deref())
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
