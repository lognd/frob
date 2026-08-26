"""The ONE `gh` (GitHub CLI) subprocess seam (docs/modules/ghio.md), mirroring
the discipline `frob.gitio` establishes for git: typed, Result-returning,
every fallible operation a value rather than a bare exception.

T-2982 part 1 (T-2983): before this module, `git grep` for `gh` invocations
across `src/frob/` returned ZERO hits -- every CI interaction was a hand-rolled
`gh run list` / `gh run view --job` / `gh api .../logs` shell-out, eyeballed
by an operator or agent. This module is the seam those callers should have
had: `preflight` classifies the environment (gh missing, unauthenticated,
no GitHub remote, ...) before any GitHub-reaching call is attempted;
`list_runs`/`view_run`/`view_job`/`job_log` wrap the individual `gh`
subcommands, each returning a named `GhError` rather than raising or handing
back an ambiguous empty string.

The measured EMPTY-LOG-FOR-A-FAILED-JOB mode (`--log-failed` returning
nothing for a job that genuinely failed, while `--log` separately refuses
because the parent RUN is still in progress even though the JOB completed)
is the reason `job_log` returns a `JobLog` record carrying an explicit
`truncated`/`empty` flag rather than a bare string -- callers must be able
to tell "no log" from "log says nothing failed" (the silent-zero class this
drive has been eliminating elsewhere; see `frob.verify`'s stale-baseline
refusal and gate UNRES rendering for the same doctrine applied here).

PART 2 (structured reporting) and PART 3 (CI result validity against the
obligation graph) are explicitly out of scope for this module (T-2984,
T-2985) -- this seam only talks to `gh` and returns typed records; it does
not cluster failures or reason about staleness.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.gitio import ProcResult, excerpt, run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

_DEFAULT_TIMEOUT_S = 30.0
_LOG_TIMEOUT_S = 60.0


# frob:doc docs/modules/ghio.md#error-types
# frob:tests tests/test_ghio.py::TestPreflight.test_not_installed
# frob:tests tests/test_ghio.py::TestJobLog.test_empty_log_for_a_failed_job_is_named
class GhError(ErrorSet):
    """Every named failure mode `frob.ghio` can hand back as a value --
    never a crash, never a silent empty result. T-2982's motivating
    incidents map onto these one-to-one: `NotInstalled` (gh missing from
    PATH), `NotAuthenticated`/`CredentialsExpired` (distinct because the
    remedy differs -- `gh auth login` vs `gh auth refresh`), `NoRemote`
    (frob must stay useful off-GitHub -- the PLATFORM001 portability
    doctrine applied to this seam), `RateLimited` (distinct from
    `NetworkUnreachable` -- the remedy differs, wait vs. check
    connectivity), `NotFound` (a run/job id that does not exist), and
    `EmptyLog` (a job that DID fail but whose log retrieval came back
    empty -- the measured 2026-08-25 incident this ticket exists to
    prevent from ever rendering as "nothing to report")."""

    NotInstalled = "gh is not installed or not on PATH"
    NotAuthenticated = "gh is not authenticated (gh auth status failed)"
    CredentialsExpired = "gh credentials have expired"
    NoRemote = "no GitHub remote configured, or this is not a GitHub repository"
    RateLimited = "GitHub API rate limit exceeded"
    NetworkUnreachable = "network unreachable while contacting GitHub"
    NotFound = "the requested run or job id was not found"
    EmptyLog = "log retrieval returned empty for a job that did not succeed"
    RunInProgress = "the parent run is still in progress; per-run logs are unavailable"
    GhFailed = "gh subprocess failed for an unclassified reason"


# frob:doc docs/modules/ghio.md#data-models
# frob:tests tests/test_ghio.py::TestPreflight.test_success
class GhEnvironment(BaseModel):
    """The result of `preflight`: whether `gh` is usable at all in this
    working tree, checked once so every other function in this module can
    assume a working `gh` rather than re-deriving this classification."""

    model_config = ConfigDict(frozen=True)

    gh_version: str
    account: str


# frob:doc docs/modules/ghio.md#data-models
# frob:tests tests/test_ghio.py::TestListRuns.test_success_parses_rows
class RunSummary(BaseModel):
    """One row of `gh run list --json`: enough to identify a run and its
    outcome without a second call."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    name: str
    status: str
    conclusion: str
    head_sha: str
    url: str


# frob:doc docs/modules/ghio.md#data-models
# frob:tests tests/test_ghio.py::TestViewRun.test_success_parses_jobs
class JobSummary(BaseModel):
    """One job belonging to a run, as reported by `gh run view --json jobs`."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    name: str
    status: str
    conclusion: str


# frob:doc docs/modules/ghio.md#data-models
# frob:tests tests/test_ghio.py::TestViewRun.test_success_parses_jobs
class RunDetail(BaseModel):
    """A single run plus its jobs, from one `gh run view <id> --json` call."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    status: str
    conclusion: str
    jobs: tuple[JobSummary, ...]


# frob:doc docs/modules/ghio.md#data-models
# frob:tests tests/test_ghio.py::TestJobLog.test_truncated_log_for_cancelled_run
class JobLog(BaseModel):
    """A job's log text, with the measured empty/truncated distinctions
    made explicit rather than left for a caller to rediscover by
    inspecting `text`. `empty=True` means the retrieval SUCCEEDED (no
    subprocess error) but returned zero bytes -- distinguishable from
    `Err(GhError.EmptyLog)`, which this module returns instead when the
    caller can determine the owning job did NOT succeed (see `job_log`'s
    docstring for exactly when each is used). `truncated=True` marks the
    measured cancelled-run case: the log exists but a failure summary
    (e.g. pytest's) may never have been written, so "the log exists" does
    not mean "the failures are in it" -- callers must not treat a
    truncated log's absence of a expected marker as a clean run."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    text: str
    empty: bool
    truncated: bool


def _classify_gh_failure(result: ProcResult) -> GhError:
    """Map a nonzero-exit `gh` invocation's stderr to a named `GhError`,
    the single place that owns the stderr-substring heuristics `gh`
    itself does not give a structured error type for -- every caller in
    this module routes through here rather than re-deriving its own
    substring checks, so a new heuristic only needs to be added once."""
    stderr = result.stderr.lower()
    if "gh: command not found" in stderr or result.returncode == 127:
        return GhError.NotInstalled
    if "auth status" in stderr and "not logged" in stderr:
        return GhError.NotAuthenticated
    if "gh auth login" in stderr and "expired" in stderr:
        return GhError.CredentialsExpired
    if "gh auth login" in stderr:
        return GhError.NotAuthenticated
    if "no default remote repository" in stderr or (
        "could not determine" in stderr and "repository" in stderr
    ):
        return GhError.NoRemote
    if "api rate limit exceeded" in stderr or "rate limit" in stderr:
        return GhError.RateLimited
    if (
        "could not resolve host" in stderr
        or "network is unreachable" in stderr
        or "connection refused" in stderr
        or "timeout" in stderr
        and "dial tcp" in stderr
    ):
        return GhError.NetworkUnreachable
    if "still in progress" in stderr:
        return GhError.RunInProgress
    if "404" in stderr or "not found" in stderr or "could not find" in stderr:
        return GhError.NotFound
    _log.warning(
        "ghio: unclassified gh failure (rc=%d): %s",
        result.returncode,
        excerpt(result.stderr),
    )
    return GhError.GhFailed


def _run_gh(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    env: Mapping[str, str] | None = None,
) -> Result[ProcResult, GhError]:
    """Spawn `gh <args>` in `cwd` via `frob.gitio.run_argv` (the one process-
    with-timeout helper in the package -- no second subprocess primitive
    lives here). Distinguishes a spawn-level failure (`gh` missing from
    PATH entirely -- `FileNotFoundError` surfaces through `run_argv` as
    `GitError.GitFailed`, remapped here to the more specific
    `GhError.NotInstalled`) from a `gh`-reported failure (nonzero exit,
    classified via `_classify_gh_failure`)."""
    argv = ("gh", *args)
    spawned = run_argv(argv, cwd=cwd, timeout_s=timeout_s, env=env)
    if spawned.is_err:
        # run_argv's only failure mode is a spawn-level problem (missing
        # binary, kill switch, timeout) -- in this seam that is almost
        # always "gh is not installed."
        _log.warning("ghio: gh spawn failed for %s", argv)
        return Err(GhError.NotInstalled)
    result = spawned.danger_ok
    if result.returncode != 0:
        error = _classify_gh_failure(result)
        _log.warning(
            "ghio: gh %s failed (rc=%d, classified=%s): %s",
            " ".join(args),
            result.returncode,
            error,
            excerpt(result.stderr),
        )
        return Err(error)
    return Ok(result)


# frob:doc docs/modules/ghio.md#public-api
# frob:tests tests/test_ghio.py::TestPreflight.test_success
# frob:tests \
# tests/test_ghio.py::TestPreflight::test_no_gh_no_auth_no_remote_never_crashes
# frob:tests \
# tests/test_ghio.py::TestPreflightIntegration::test_real_subprocess_seam_against_a_fak\
# e_gh_binary
def preflight(root: Path) -> Result[GhEnvironment, GhError]:
    """Classify whether `gh` is usable at all under `root`, before any
    call that actually reaches GitHub is attempted: not installed, not
    authenticated, credentials expired, or no GitHub remote (frob must
    stay useful off-GitHub -- the same portability doctrine PLATFORM001
    enforces elsewhere). Every other public function in this module
    should be preceded by a `preflight` call by its caller (or accept the
    same `GhError` set back directly, since each individually re-checks
    via `_run_gh`) -- `preflight` exists so a caller that only wants to
    know "can I even try" does not need to make a throwaway API call to
    find out."""
    version_result = _run_gh(("--version",), cwd=root)
    if version_result.is_err:
        return Err(version_result.danger_err)
    version_line = version_result.danger_ok.stdout.splitlines()[0] if (
        version_result.danger_ok.stdout.splitlines()
    ) else ""

    auth_result = _run_gh(("auth", "status"), cwd=root)
    if auth_result.is_err:
        return Err(auth_result.danger_err)

    remote_result = _run_gh(("repo", "view", "--json", "nameWithOwner"), cwd=root)
    if remote_result.is_err:
        return Err(remote_result.danger_err)
    try:
        parsed = json.loads(remote_result.danger_ok.stdout)
        account = str(parsed.get("nameWithOwner", ""))
    except (json.JSONDecodeError, AttributeError):
        _log.warning("ghio: preflight: could not parse repo view output")
        account = ""

    _log.info("ghio: preflight ok (version=%r, repo=%r)", version_line, account)
    return Ok(GhEnvironment(gh_version=version_line, account=account))


# frob:doc docs/modules/ghio.md#public-api
# frob:tests tests/test_ghio.py::TestListRuns.test_success_parses_rows
# frob:tests tests/test_ghio.py::TestListRuns.test_not_found_run_list_failure
def list_runs(
    root: Path, *, limit: int = 20, workflow: str | None = None
) -> Result[tuple[RunSummary, ...], GhError]:
    """`gh run list --json ...` for the repo under `root`, newest first
    (gh's own default order). `workflow`, when given, narrows to one
    workflow file/name (`gh run list --workflow`)."""
    fields = "databaseId,name,status,conclusion,headSha,url"
    args = ["run", "list", "--json", fields, "--limit", str(limit)]
    if workflow is not None:
        args.extend(("--workflow", workflow))
    result = _run_gh(tuple(args), cwd=root)
    if result.is_err:
        return Err(result.danger_err)
    try:
        rows = json.loads(result.danger_ok.stdout)
    except json.JSONDecodeError:
        _log.warning("ghio: list_runs: could not parse gh run list JSON")
        return Err(GhError.GhFailed)
    runs = tuple(
        RunSummary(
            run_id=str(row.get("databaseId", "")),
            name=str(row.get("name", "")),
            status=str(row.get("status", "")),
            conclusion=str(row.get("conclusion", "") or ""),
            head_sha=str(row.get("headSha", "")),
            url=str(row.get("url", "")),
        )
        for row in rows
    )
    return Ok(runs)


# frob:doc docs/modules/ghio.md#public-api
# frob:tests tests/test_ghio.py::TestViewRun.test_success_parses_jobs
# frob:tests tests/test_ghio.py::TestViewRun.test_run_not_found
def view_run(root: Path, run_id: str) -> Result[RunDetail, GhError]:
    """`gh run view <run_id> --json status,conclusion,jobs`: one run plus
    every job it contains, in a single call. `Err(GhError.NotFound)` for
    an id that does not exist (mapped from gh's own "could not find any
    workflow run" / HTTP 404 stderr via `_classify_gh_failure`)."""
    result = _run_gh(
        ("run", "view", run_id, "--json", "status,conclusion,jobs"), cwd=root
    )
    if result.is_err:
        return Err(result.danger_err)
    try:
        parsed = json.loads(result.danger_ok.stdout)
    except json.JSONDecodeError:
        _log.warning("ghio: view_run: could not parse gh run view JSON")
        return Err(GhError.GhFailed)
    jobs = tuple(
        JobSummary(
            job_id=str(job.get("databaseId", "")),
            name=str(job.get("name", "")),
            status=str(job.get("status", "")),
            conclusion=str(job.get("conclusion", "") or ""),
        )
        for job in parsed.get("jobs", [])
    )
    return Ok(
        RunDetail(
            run_id=run_id,
            status=str(parsed.get("status", "")),
            conclusion=str(parsed.get("conclusion", "") or ""),
            jobs=jobs,
        )
    )


# frob:doc docs/modules/ghio.md#public-api
# frob:tests tests/test_ghio.py::TestJobLog.test_empty_log_for_a_failed_job_is_named
# frob:tests tests/test_ghio.py::TestJobLog.test_truncated_log_for_cancelled_run
# frob:tests tests/test_ghio.py::TestJobLog.test_normal_log_is_not_truncated_not_empty
def job_log(root: Path, run_id: str, job_id: str) -> Result[JobLog, GhError]:
    """A single job's log text, routed through the job-scoped REST route
    (`gh api repos/{owner}/{repo}/actions/jobs/{job_id}/logs`) rather than
    `gh run view --log`, per the 2026-08-25 measurement recorded on
    T-2982: `gh run view --log` refuses outright while the PARENT run is
    still in progress, even when the requested JOB has already completed
    ("run <id> is still in progress; logs will be available when it is
    complete") -- that refusal is mapped to `GhError.RunInProgress` by
    `_classify_gh_failure` when it does occur (e.g. a caller reaching this
    function for a job whose run has not yet finished at all). The
    job-scoped `gh api .../actions/jobs/<job_id>/logs` route does NOT
    share that refusal: it succeeds for a completed job while its run is
    still going (measured: 78KB and 109KB retrievals), and returns a
    genuine HTTP 404 -- mapped to `GhError.NotFound` -- only if the JOB
    itself is still in progress.

    `owner/repo` is resolved via `gh repo view --json nameWithOwner`
    first (one extra call) rather than assumed, since a caller may be
    running this against a fork or a repo with a nonstandard remote name.

    Distinguishes three outcomes rather than collapsing them into one
    string, per T-2982's measured EMPTY-LOG incident (`--log-failed`
    returned nothing for a job that had genuinely failed):
      - the API call itself fails (auth/network/not-found/rate-limit) ->
        `Err(GhError...)`, same taxonomy as every other call here;
      - the call SUCCEEDS but returns zero bytes for a job whose own
        `conclusion` was not `success` -> `Err(GhError.EmptyLog)`, the
        distinguishable failure this ticket exists to add -- never handed
        back as `Ok(JobLog(text="", ...))` as if it were a clean result;
      - the call succeeds and returns text -> `Ok(JobLog(...))`, with
        `truncated` set when the OWNING run's status/conclusion indicates
        it was cancelled (a cancelled run's log is retrievable but may
        never have reached the point of writing a failure summary, so its
        presence does not mean the failures are captured in it -- callers
        must not read "log has content" as "log has the failure").

    Split into `_resolve_owner_repo` (the extra `gh repo view` call) and
    `_classify_log_result` (the empty/truncated decision) so this
    function itself stays a short orchestration of the two, per this
    module's own ARCH001 line budget."""
    owner_result = _resolve_owner_repo(root)
    if owner_result.is_err:
        return Err(owner_result.danger_err)
    owner_repo = owner_result.danger_ok

    log_result = _run_gh(
        ("api", f"repos/{owner_repo}/actions/jobs/{job_id}/logs"),
        cwd=root,
        timeout_s=_LOG_TIMEOUT_S,
    )
    if log_result.is_err:
        return Err(log_result.danger_err)
    text = log_result.danger_ok.stdout

    run_result = view_run(root, run_id)
    owning_run = run_result.danger_ok if run_result.is_ok else None
    return _classify_log_result(job_id=job_id, text=text, owning_run=owning_run)


def _resolve_owner_repo(root: Path) -> Result[str, GhError]:
    """`gh repo view --json nameWithOwner`, the one extra call `job_log`
    needs to build the job-scoped `gh api` route -- extracted from
    `job_log` to keep that function under this module's own ARCH001 line
    budget."""
    repo_result = _run_gh(("repo", "view", "--json", "nameWithOwner"), cwd=root)
    if repo_result.is_err:
        return Err(repo_result.danger_err)
    try:
        owner_repo = json.loads(repo_result.danger_ok.stdout).get("nameWithOwner", "")
    except (json.JSONDecodeError, AttributeError):
        _log.warning("ghio: job_log: could not resolve owner/repo")
        return Err(GhError.GhFailed)
    if not owner_repo:
        return Err(GhError.NoRemote)
    return Ok(owner_repo)


def _classify_log_result(
    *, job_id: str, text: str, owning_run: RunDetail | None
) -> Result[JobLog, GhError]:
    """The empty/truncated decision `job_log` needs once it has the raw
    log text and (best-effort) the owning run's detail -- extracted so
    `job_log` itself stays a short orchestration, per this module's own
    ARCH001 line budget. See `job_log`'s own docstring for the three
    outcomes this distinguishes."""
    owning_job = None
    if owning_run is not None:
        owning_job = next((j for j in owning_run.jobs if j.job_id == job_id), None)

    if not text:
        job_failed = owning_job is not None and owning_job.conclusion not in (
            "success",
            "",
        )
        if job_failed:
            _log.warning(
                "ghio: job_log: EMPTY log for job %s which did NOT succeed "
                "(conclusion=%r) -- reporting as EmptyLog, not a clean result",
                job_id,
                owning_job.conclusion if owning_job else None,
            )
            return Err(GhError.EmptyLog)
        _log.info("ghio: job_log: empty log for job %s (no failure evidence)", job_id)
        return Ok(JobLog(job_id=job_id, text="", empty=True, truncated=False))

    truncated = owning_run is not None and owning_run.conclusion == "cancelled"
    if truncated:
        _log.info(
            "ghio: job_log: log for job %s belongs to a CANCELLED run -- "
            "marking truncated (failure summary may not have been written)",
            job_id,
        )
    return Ok(JobLog(job_id=job_id, text=text, empty=False, truncated=truncated))


__all__ = [
    "GhEnvironment",
    "GhError",
    "JobLog",
    "JobSummary",
    "RunDetail",
    "RunSummary",
    "job_log",
    "list_runs",
    "preflight",
    "view_run",
]
