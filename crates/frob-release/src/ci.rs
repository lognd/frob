//! CI status of the commit a release would ship, read through `gh api` (`releases.md` 4 and 6a).
//!
//! [`check_tip`] asks GitHub for the check runs and the combined commit status of one sha and
//! folds them into a [`CiState`]: green, red (with the failing names and links), pending, or
//! unknown with the exact reason and remedy. It never fails and never guesses: an answer that
//! cannot be read is [`CiState::Unknown`], which `release status` reports as Unresolved (and as a
//! blocker unless `[release] require_ci = false`). `gh` is spawned through `gob-exec` (argv, no
//! shell); the parsing and classification are pure and tested against recorded JSON.

// frob:ticket 01M4069WYA9D1EGVEBC4PT3KZB
use std::path::Path;
use std::time::Duration;

use gob_exec::{ExecError, Outcome, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Wall-clock limit for one `gh api` call.
const GH_TIMEOUT: Duration = Duration::from_secs(30);

/// Remedy shared by every "cannot ask GitHub" answer: the knob that turns unknown into a warning.
const REQUIRE_CI_HINT: &str = "or set `[release] require_ci = false` in frob.toml to report it as Unresolved without blocking";

/// One failing check: what failed, how, and where to look.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct CiFailure {
    /// The check run name or status context.
    pub name: String,
    /// The conclusion or state (`failure`, `cancelled`, `timed_out`, ...).
    pub conclusion: String,
    /// A link to the run, when GitHub gave one.
    pub url: Option<String>,
}

/// CI could not be read, with the exact reason and what to do about it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema, thiserror::Error)]
#[error("{reason}")]
pub struct CiUnknown {
    /// Exactly why (the gh exit code and first stderr line, the remote, the missing checks).
    pub reason: String,
    /// The command or setting that resolves it.
    pub remedy: String,
}

/// The CI verdict for one commit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CiState {
    /// Every check completed and succeeded or was skipped, and at least one exists.
    Green {
        /// How many checks were looked at.
        checks: usize,
    },
    /// At least one check failed, was cancelled or timed out.
    Red {
        /// The failing checks.
        failures: Vec<CiFailure>,
    },
    /// Nothing failed but some checks have not finished.
    Pending {
        /// Names of the unfinished checks.
        running: Vec<String>,
    },
    /// The answer could not be read.
    Unknown(CiUnknown),
}

/// The CI facts [`crate::status::assess`] needs: which commit, what CI said, whether unknown blocks.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CiFacts {
    /// The base-branch tip inspected; `None` when the branch did not resolve.
    pub sha: Option<String>,
    /// What CI said.
    pub state: CiState,
    /// `[release] require_ci`: whether an unknown result blocks the release.
    pub require: bool,
}

/// A GitHub repository named by a remote URL.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GithubRepo {
    /// Owner (user or organisation).
    pub owner: String,
    /// Repository name without `.git`.
    pub name: String,
}

/// `user:password@` stripped from a URL so credentials never reach a message or a log.
fn redact_url(url: &str) -> String {
    match (url.find("://"), url.find('@')) {
        (Some(s), Some(a)) if a > s && !url[s + 3..a].contains('/') => {
            format!("{}{}", &url[..s + 3], &url[a + 1..])
        }
        _ => url.to_owned(),
    }
}

/// The GitHub owner and repository of a remote URL (https, ssh, scp-like or git form), or why it is not one.
///
/// # Errors
/// [`CiUnknown`] when the host is not `github.com` or the path is not `owner/repo`.
pub fn parse_remote(url: &str) -> Result<GithubRepo, CiUnknown> {
    let not_github = || CiUnknown {
        reason: format!(
            "origin is `{}`, which is not a github.com remote; CI status is read through the GitHub CLI only",
            redact_url(url)
        ),
        remedy: format!(
            "point origin at GitHub (`git remote set-url origin https://github.com/<owner>/<repo>.git`), {REQUIRE_CI_HINT}"
        ),
    };
    let trimmed = url.trim();
    let (host, path) = if let Some((_, rest)) = trimmed.split_once("://") {
        let (auth_host, path) = rest.split_once('/').ok_or_else(not_github)?;
        let host = auth_host.rsplit('@').next().unwrap_or(auth_host);
        (host.split(':').next().unwrap_or(host), path)
    } else if let Some((auth_host, path)) = trimmed.split_once(':') {
        (auth_host.rsplit('@').next().unwrap_or(auth_host), path)
    } else {
        return Err(not_github());
    };
    if !host.eq_ignore_ascii_case("github.com") {
        return Err(not_github());
    }
    let path = path.trim_matches('/');
    let path = path.strip_suffix(".git").unwrap_or(path);
    match path.split('/').collect::<Vec<_>>().as_slice() {
        [owner, name] if !owner.is_empty() && !name.is_empty() => Ok(GithubRepo {
            owner: (*owner).to_owned(),
            name: (*name).to_owned(),
        }),
        _ => Err(not_github()),
    }
}

/// One page of `commits/{sha}/check-runs`.
#[derive(Debug, Deserialize)]
struct CheckRunsPage {
    #[serde(default)]
    check_runs: Vec<CheckRun>,
}

/// One check run as GitHub reports it.
#[derive(Debug, Deserialize)]
struct CheckRun {
    name: String,
    #[serde(default)]
    status: String,
    conclusion: Option<String>,
    html_url: Option<String>,
    details_url: Option<String>,
}

/// One page of `commits/{sha}/status`.
#[derive(Debug, Deserialize)]
struct StatusPage {
    #[serde(default)]
    statuses: Vec<CommitStatus>,
}

/// One legacy commit status.
#[derive(Debug, Deserialize)]
struct CommitStatus {
    context: String,
    state: String,
    target_url: Option<String>,
}

/// How one check came out.
#[derive(Debug, PartialEq, Eq)]
enum Verdict {
    Pass,
    Pending,
    Fail(String),
}

/// A check with its name, link and verdict, whichever endpoint it came from.
#[derive(Debug)]
struct Check {
    name: String,
    url: Option<String>,
    verdict: Verdict,
}

impl From<CheckRun> for Check {
    /// Completed `success`, `skipped` and `neutral` pass; unfinished is pending; every other conclusion fails (unknown is never green).
    fn from(r: CheckRun) -> Self {
        let verdict = if r.status == "completed" {
            match r.conclusion.as_deref() {
                Some("success" | "skipped" | "neutral") => Verdict::Pass,
                Some(other) => Verdict::Fail(other.to_owned()),
                None => Verdict::Fail("no conclusion".to_owned()),
            }
        } else {
            Verdict::Pending
        };
        Self {
            name: r.name,
            url: r.html_url.or(r.details_url),
            verdict,
        }
    }
}

impl From<CommitStatus> for Check {
    /// `success` passes, `pending` waits, `failure`, `error` and anything else fail.
    fn from(s: CommitStatus) -> Self {
        let verdict = match s.state.as_str() {
            "success" => Verdict::Pass,
            "pending" => Verdict::Pending,
            other => Verdict::Fail(other.to_owned()),
        };
        Self {
            name: s.context,
            url: s.target_url,
            verdict,
        }
    }
}

/// Fold checks into a state: any failure is red, else any unfinished is pending, else green; none at all is unknown.
fn classify(checks: Vec<Check>, sha: &str) -> CiState {
    if checks.is_empty() {
        return CiState::Unknown(CiUnknown {
            reason: format!("GitHub reports no checks or statuses for commit {sha}"),
            remedy: format!(
                "make CI run for that commit (push it, or add a workflow triggered on push), {REQUIRE_CI_HINT}"
            ),
        });
    }
    let total = checks.len();
    let mut failures = Vec::new();
    let mut running = Vec::new();
    for c in checks {
        match c.verdict {
            Verdict::Pass => {}
            Verdict::Pending => running.push(c.name),
            Verdict::Fail(conclusion) => failures.push(CiFailure {
                name: c.name,
                conclusion,
                url: c.url,
            }),
        }
    }
    if !failures.is_empty() {
        CiState::Red { failures }
    } else if !running.is_empty() {
        CiState::Pending { running }
    } else {
        CiState::Green { checks: total }
    }
}

/// Parse `gh api --paginate` output, which is one JSON document per page, concatenated.
fn pages<T: for<'de> Deserialize<'de>>(text: &str, what: &str) -> Result<Vec<T>, CiUnknown> {
    serde_json::Deserializer::from_str(text)
        .into_iter::<T>()
        .collect::<Result<Vec<T>, _>>()
        .map_err(|e| CiUnknown {
            reason: format!("gh returned {what} that could not be read: {e}"),
            remedy: format!("update the GitHub CLI (`gh --version`) and rerun, {REQUIRE_CI_HINT}"),
        })
}

/// The first non-empty line of `text`, trimmed, for one-line reasons.
fn first_line(text: &str) -> &str {
    text.lines()
        .map(str::trim)
        .find(|l| !l.is_empty())
        .unwrap_or("")
}

/// Map a failed `gh api` call (exit code and stderr) to the reason and the remedy.
fn gh_failure(code: i32, stderr: &str, sha: &str, repo: &GithubRepo) -> CiUnknown {
    let line = first_line(stderr);
    let low = stderr.to_lowercase();
    let has = |needles: &[&str]| needles.iter().any(|n| low.contains(n));
    let slug = format!("{}/{}", repo.owner, repo.name);
    let (what, remedy) = if has(&[
        "gh auth login",
        "not logged in",
        "http 401",
        "bad credentials",
        "authentication",
    ]) {
        (
            "the GitHub CLI is not authenticated",
            "run `gh auth login` (or export GH_TOKEN with `repo` read access)".to_owned(),
        )
    } else if has(&["no commit found for sha", "http 422"]) {
        (
            "GitHub does not know this commit",
            format!("push the base branch to origin so CI runs for {sha}"),
        )
    } else if has(&["http 404"]) {
        (
            "the repository was not found or the token cannot see it",
            format!("check that {slug} exists and `gh auth status` has access to it"),
        )
    } else if has(&[
        "error connecting",
        "could not resolve",
        "no such host",
        "network is unreachable",
        "dial tcp",
        "connection refused",
        "i/o timeout",
        "timed out",
    ]) {
        (
            "GitHub could not be reached (no network)",
            "restore network access and rerun".to_owned(),
        )
    } else if has(&["rate limit"]) {
        (
            "GitHub rate-limited the request",
            "wait for the limit to reset or authenticate with `gh auth login`".to_owned(),
        )
    } else if has(&["http 403"]) {
        (
            "the token is not allowed to read checks",
            "use a token with `repo` (or `checks:read`) access: `gh auth login`".to_owned(),
        )
    } else {
        (
            "the GitHub CLI failed",
            "run the same `gh api` call by hand to see the error".to_owned(),
        )
    };
    CiUnknown {
        reason: format!("{what}: `gh api` exited {code}: {line}"),
        remedy: format!("{remedy}, {REQUIRE_CI_HINT}"),
    }
}

/// Run `gh api --paginate <endpoint>` and return its stdout, or why it could not answer.
fn gh_api(
    runner: &Runner,
    gh: &Program,
    cwd: &Path,
    endpoint: &str,
    sha: &str,
    repo: &GithubRepo,
) -> Result<String, CiUnknown> {
    let spec = Spec {
        program: gh.clone(),
        args: [
            "api",
            "--paginate",
            "-H",
            "Accept: application/vnd.github+json",
            endpoint,
        ]
        .map(str::to_owned)
        .to_vec(),
        cwd: Some(cwd.to_path_buf()),
        env: vec![
            ("GH_PROMPT_DISABLED".to_owned(), "1".to_owned()),
            ("GH_NO_UPDATE_NOTIFIER".to_owned(), "1".to_owned()),
            ("NO_COLOR".to_owned(), "1".to_owned()),
        ],
        timeout: GH_TIMEOUT,
        capture: true,
    };
    tracing::debug!(endpoint, "asking gh for CI status");
    match runner.run(&spec) {
        Ok(out) => match out.status {
            Outcome::Exited(0) => Ok(out.stdout),
            Outcome::Exited(code) => Err(gh_failure(code, &out.stderr, sha, repo)),
            Outcome::Signaled => Err(CiUnknown {
                reason: "`gh api` was killed by a signal".to_owned(),
                remedy: format!("rerun; {REQUIRE_CI_HINT}"),
            }),
            Outcome::TimedOut => Err(CiUnknown {
                reason: format!("`gh api` did not answer within {}s", GH_TIMEOUT.as_secs()),
                remedy: format!("check the network and rerun, {REQUIRE_CI_HINT}"),
            }),
        },
        Err(ExecError::NotFound { .. }) => Err(CiUnknown {
            reason: "the GitHub CLI (`gh`) is not installed or not on PATH".to_owned(),
            remedy: format!(
                "install it (https://cli.github.com) and run `gh auth login`, {REQUIRE_CI_HINT}"
            ),
        }),
        Err(e) => Err(CiUnknown {
            reason: format!("`gh` could not be run: {e}"),
            remedy: format!("fix the error above and rerun, {REQUIRE_CI_HINT}"),
        }),
    }
}

/// Read the check runs and the combined status of `sha` through `gh` (argv only), as one verdict.
///
/// `remote_url` is origin's URL (`None` when there is no origin). Never fails: whatever cannot be
/// read is [`CiState::Unknown`] with its reason and remedy.
pub fn check_tip(
    runner: &Runner,
    gh: &Program,
    cwd: &Path,
    remote_url: Option<&str>,
    sha: &str,
) -> CiState {
    let state = match query(runner, gh, cwd, remote_url, sha) {
        Ok(s) => s,
        Err(u) => CiState::Unknown(u),
    };
    tracing::info!(sha, state = ?std::mem::discriminant(&state), "CI status read");
    state
}

/// The fallible body of [`check_tip`].
fn query(
    runner: &Runner,
    gh: &Program,
    cwd: &Path,
    remote_url: Option<&str>,
    sha: &str,
) -> Result<CiState, CiUnknown> {
    let url = remote_url.ok_or_else(|| CiUnknown {
        reason: "there is no `origin` remote, so there is no repository to ask".to_owned(),
        remedy: format!("add one (`git remote add origin https://github.com/<owner>/<repo>.git`), {REQUIRE_CI_HINT}"),
    })?;
    let repo = parse_remote(url)?;
    let base = format!("repos/{}/{}/commits/{sha}", repo.owner, repo.name);
    let runs = gh_api(
        runner,
        gh,
        cwd,
        &format!("{base}/check-runs?per_page=100"),
        sha,
        &repo,
    )?;
    let status = gh_api(
        runner,
        gh,
        cwd,
        &format!("{base}/status?per_page=100"),
        sha,
        &repo,
    )?;
    let mut checks: Vec<Check> = pages::<CheckRunsPage>(&runs, "check runs")?
        .into_iter()
        .flat_map(|p| p.check_runs)
        .map(Check::from)
        .collect();
    checks.extend(
        pages::<StatusPage>(&status, "commit statuses")?
            .into_iter()
            .flat_map(|p| p.statuses)
            .map(Check::from),
    );
    Ok(classify(checks, sha))
}

/// One workflow run as `actions/runs` lists it.
#[derive(Deserialize)]
struct RawRun {
    head_sha: String,
    status: Option<String>,
    conclusion: Option<String>,
}

/// A page of `actions/runs`.
#[derive(Deserialize)]
struct RunsPage {
    workflow_runs: Vec<RawRun>,
}

// frob:ticket 01M4GWS3GBJTFXFEGSNFB7J4FQ
/// The latest workflow runs of `branch` on the GitHub repository behind `remote_url`, newest first.
///
/// This feeds [`crate::culprit::find_culprit`]. Like [`check_tip`] it never guesses: an answer that
/// cannot be read is a [`CiUnknown`] with the reason and remedy.
///
/// # Errors
/// [`CiUnknown`] when there is no GitHub remote, `gh` fails, or its answer cannot be read.
pub fn list_runs(
    runner: &Runner,
    gh: &Program,
    cwd: &Path,
    remote_url: Option<&str>,
    branch: &str,
) -> Result<Vec<crate::culprit::RunRecord>, CiUnknown> {
    let url = remote_url.ok_or_else(|| CiUnknown {
        reason: "there is no `origin` remote, so there is no repository to ask".to_owned(),
        remedy: "add one (`git remote add origin https://github.com/<owner>/<repo>.git`)"
            .to_owned(),
    })?;
    let repo = parse_remote(url)?;
    let endpoint = format!(
        "repos/{}/{}/actions/runs?branch={branch}&per_page=100",
        repo.owner, repo.name
    );
    let body = gh_api(runner, gh, cwd, &endpoint, branch, &repo)?;
    let runs: Vec<crate::culprit::RunRecord> = pages::<RunsPage>(&body, "workflow runs")?
        .into_iter()
        .flat_map(|p| p.workflow_runs)
        .map(|r| crate::culprit::RunRecord {
            verdict: crate::culprit::Verdict::from_run(
                r.status.as_deref(),
                r.conclusion.as_deref(),
            ),
            sha: r.head_sha,
        })
        .collect();
    tracing::info!(branch, runs = runs.len(), "workflow runs read");
    Ok(runs)
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use gob_exec::Limits;
    use std::os::unix::fs::PermissionsExt;

    /// A directory holding a stub `gh` that prints recorded JSON per endpoint, or fails on request.
    struct FakeGh {
        dir: tempfile::TempDir,
    }

    impl FakeGh {
        /// `runs` and `status` are the recorded bodies; `fail` is `(exit code, stderr)` for every call.
        fn new(runs: &str, status: &str, fail: Option<(i32, &str)>) -> Self {
            let dir = tempfile::tempdir().expect("tempdir");
            std::fs::write(dir.path().join("runs.json"), runs).expect("runs");
            std::fs::write(dir.path().join("status.json"), status).expect("status");
            let d = dir.path().display();
            let body = match fail {
                Some((code, err)) => format!("echo '{err}' >&2\nexit {code}\n"),
                None => format!(
                    "case \"$*\" in\n*actions/runs*) cat '{d}/runs.json';;\n*actions/runs*) cat '{d}/runs.json';;\n*check-runs*) cat '{d}/runs.json';;\n*/status*) cat '{d}/status.json';;\n*) exit 9;;\nesac\n"
                ),
            };
            let path = dir.path().join("gh");
            std::fs::write(&path, format!("#!/bin/sh\n{body}")).expect("script");
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).expect("chmod");
            Self { dir }
        }

        fn program(&self) -> Program {
            Program::Hook {
                path: self.dir.path().join("gh"),
            }
        }

        fn tip(&self, url: Option<&str>) -> CiState {
            check_tip(
                &Runner::new(Limits { jobs: 1 }),
                &self.program(),
                self.dir.path(),
                url,
                "abc1234",
            )
        }
    }

    const ORIGIN: Option<&str> = Some("git@github.com:acme/widget.git");
    const NO_STATUS: &str = r#"{"state":"pending","total_count":0,"statuses":[]}"#;

    fn runs(items: &[(&str, &str, Option<&str>)]) -> String {
        let items: Vec<String> = items
            .iter()
            .map(|(name, status, conclusion)| {
                let c = conclusion.map_or("null".to_owned(), |c| format!("\"{c}\""));
                format!(
                    r#"{{"name":"{name}","status":"{status}","conclusion":{c},"html_url":"https://github.com/acme/widget/runs/{name}"}}"#
                )
            })
            .collect();
        format!(
            r#"{{"total_count":{},"check_runs":[{}]}}"#,
            items.len(),
            items.join(",")
        )
    }

    // frob:ticket 01M4GWS3GBJTFXFEGSNFB7J4FQ
    // frob:tests crates/frob-release/src/ci.rs::list_runs
    #[test]
    fn workflow_runs_become_verdict_records() {
        use crate::culprit::Verdict;
        let body = r#"{"workflow_runs":[
            {"head_sha":"aaa","status":"completed","conclusion":"failure"},
            {"head_sha":"bbb","status":"in_progress","conclusion":null},
            {"head_sha":"ccc","status":"completed","conclusion":"success"}]}"#;
        let fake = FakeGh::new(body, NO_STATUS, None);
        let runs = list_runs(
            &Runner::new(Limits { jobs: 1 }),
            &fake.program(),
            fake.dir.path(),
            ORIGIN,
            "experimental",
        )
        .expect("runs");
        let got: Vec<(&str, Verdict)> = runs.iter().map(|r| (r.sha.as_str(), r.verdict)).collect();
        assert_eq!(
            got,
            [
                ("aaa", Verdict::Red),
                ("bbb", Verdict::Unknown),
                ("ccc", Verdict::Green)
            ]
        );
        let none = list_runs(
            &Runner::new(Limits { jobs: 1 }),
            &fake.program(),
            fake.dir.path(),
            None,
            "experimental",
        );
        assert!(none.is_err());
    }

    fn unknown(s: CiState) -> CiUnknown {
        match s {
            CiState::Unknown(u) => u,
            other => panic!("expected unknown, got {other:?}"),
        }
    }

    #[test]
    fn green_when_every_check_succeeded_or_was_skipped() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let body = runs(&[
            ("build", "completed", Some("success")),
            ("docs", "completed", Some("skipped")),
        ]);
        let fake = FakeGh::new(&body, NO_STATUS, None);
        assert_eq!(fake.tip(ORIGIN), CiState::Green { checks: 2 });
    }

    #[test]
    fn red_names_every_failing_check_with_its_link() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let body = runs(&[
            ("build", "completed", Some("success")),
            ("lint", "completed", Some("failure")),
            ("slow", "completed", Some("timed_out")),
            ("dist", "completed", Some("cancelled")),
        ]);
        let fake = FakeGh::new(&body, NO_STATUS, None);
        let CiState::Red { failures } = fake.tip(ORIGIN) else {
            panic!("expected red");
        };
        let named: Vec<(&str, &str)> = failures
            .iter()
            .map(|f| (f.name.as_str(), f.conclusion.as_str()))
            .collect();
        assert_eq!(
            named,
            [
                ("lint", "failure"),
                ("slow", "timed_out"),
                ("dist", "cancelled")
            ]
        );
        assert_eq!(
            failures[0].url.as_deref(),
            Some("https://github.com/acme/widget/runs/lint")
        );
    }

    #[test]
    fn a_failing_legacy_status_is_red_too() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let status = r#"{"state":"failure","total_count":1,"statuses":[{"context":"ci/legacy","state":"failure","target_url":"https://ci.example/1"}]}"#;
        let fake = FakeGh::new(
            &runs(&[("build", "completed", Some("success"))]),
            status,
            None,
        );
        let CiState::Red { failures } = fake.tip(ORIGIN) else {
            panic!("expected red");
        };
        assert_eq!(failures[0].name, "ci/legacy");
    }

    #[test]
    fn pending_when_a_check_has_not_finished_and_nothing_failed() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let body = runs(&[
            ("build", "completed", Some("success")),
            ("test", "in_progress", None),
        ]);
        let fake = FakeGh::new(&body, NO_STATUS, None);
        assert_eq!(
            fake.tip(ORIGIN),
            CiState::Pending {
                running: vec!["test".to_owned()]
            }
        );
    }

    #[test]
    fn red_wins_over_pending() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let body = runs(&[
            ("test", "in_progress", None),
            ("lint", "completed", Some("failure")),
        ]);
        let fake = FakeGh::new(&body, NO_STATUS, None);
        assert!(matches!(fake.tip(ORIGIN), CiState::Red { .. }));
    }

    #[test]
    fn an_unrecognised_conclusion_is_red_never_green() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let body = runs(&[("odd", "completed", Some("something_new"))]);
        let fake = FakeGh::new(&body, NO_STATUS, None);
        assert!(matches!(fake.tip(ORIGIN), CiState::Red { .. }));
    }

    #[test]
    fn no_checks_at_all_is_unknown() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let fake = FakeGh::new(&runs(&[]), NO_STATUS, None);
        let u = unknown(fake.tip(ORIGIN));
        assert!(
            u.reason.contains("no checks") && u.reason.contains("abc1234"),
            "{u:?}"
        );
        assert!(u.remedy.contains("require_ci"));
    }

    #[test]
    fn gh_missing_is_unknown_with_the_install_remedy() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let dir = tempfile::tempdir().expect("tempdir");
        let s = check_tip(
            &Runner::new(Limits { jobs: 1 }),
            &Program::Hook {
                path: dir.path().join("no-such-gh"),
            },
            dir.path(),
            ORIGIN,
            "abc1234",
        );
        let u = unknown(s);
        assert!(u.reason.contains("not installed"), "{u:?}");
        assert!(u.remedy.contains("gh auth login"));
    }

    #[test]
    fn gh_unauthenticated_reports_exit_code_stderr_and_the_login_remedy() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let fake = FakeGh::new(
            "",
            "",
            Some((
                4,
                "To get started with GitHub CLI, please run:  gh auth login",
            )),
        );
        let u = unknown(fake.tip(ORIGIN));
        assert!(u.reason.contains("not authenticated"), "{u:?}");
        assert!(u.reason.contains("exited 4"), "{u:?}");
        assert!(u.reason.contains("gh auth login"), "{u:?}");
        assert!(u.remedy.starts_with("run `gh auth login`"), "{u:?}");
    }

    #[test]
    fn no_network_is_unknown_with_the_exit_code() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let fake = FakeGh::new("", "", Some((1, "error connecting to api.github.com")));
        let u = unknown(fake.tip(ORIGIN));
        assert!(
            u.reason.contains("no network") && u.reason.contains("exited 1"),
            "{u:?}"
        );
    }

    #[test]
    fn an_unpushed_commit_says_to_push() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let fake = FakeGh::new(
            "",
            "",
            Some((1, "gh: No commit found for SHA: abc1234 (HTTP 422)")),
        );
        let u = unknown(fake.tip(ORIGIN));
        assert!(u.remedy.contains("push the base branch"), "{u:?}");
    }

    #[test]
    fn a_non_github_remote_is_unknown_without_spawning_gh() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let fake = FakeGh::new("", "", None);
        let runner = Runner::new(Limits { jobs: 1 });
        let s = check_tip(
            &runner,
            &fake.program(),
            fake.dir.path(),
            Some("https://user:secret@gitlab.com/acme/widget.git"),
            "abc1234",
        );
        let u = unknown(s);
        assert!(u.reason.contains("not a github.com remote"), "{u:?}");
        assert!(!u.reason.contains("secret"), "credentials leaked: {u:?}");
        assert_eq!(runner.spawn_count().0, 0);
    }

    #[test]
    fn no_origin_is_unknown() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let fake = FakeGh::new("", "", None);
        let u = unknown(fake.tip(None));
        assert!(u.reason.contains("no `origin` remote"), "{u:?}");
    }

    #[test]
    fn paginated_output_is_read_page_by_page() {
        // frob:tests crates/frob-release/src/ci.rs::check_tip
        let two = format!(
            "{}\n{}",
            runs(&[("a", "completed", Some("success"))]),
            runs(&[("b", "completed", Some("success"))])
        );
        let fake = FakeGh::new(&two, NO_STATUS, None);
        assert_eq!(fake.tip(ORIGIN), CiState::Green { checks: 2 });
    }

    #[test]
    fn remote_urls_of_every_github_form_parse() {
        // frob:tests crates/frob-release/src/ci.rs::parse_remote
        for url in [
            "https://github.com/acme/widget.git",
            "https://github.com/acme/widget",
            "https://tok@github.com/acme/widget.git",
            "git@github.com:acme/widget.git",
            "ssh://git@github.com/acme/widget.git",
            "git://github.com/acme/widget",
        ] {
            let r = parse_remote(url).unwrap_or_else(|e| panic!("{url}: {e}"));
            assert_eq!(
                (r.owner.as_str(), r.name.as_str()),
                ("acme", "widget"),
                "{url}"
            );
        }
        for url in [
            "https://gitlab.com/acme/widget.git",
            "git@bitbucket.org:acme/widget.git",
            "/srv/git/widget.git",
            "https://github.com/acme",
        ] {
            assert!(parse_remote(url).is_err(), "{url}");
        }
    }
}
