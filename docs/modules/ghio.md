# frob.ghio -- the GitHub/CI subprocess seam

One sentence: `frob.ghio` is the single, typed, Result-returning seam for
every `gh` (GitHub CLI) invocation frob makes, mirroring the discipline
`frob.gitio` established for git -- no scattered `gh` shell-outs, every
failure mode a named value, and an empty log distinguishable from a clean
one.

## Why (T-2982/T-2983)

Before this module, `git grep` for `gh` invocations across `src/frob/`
returned ZERO hits. Every CI interaction in the drive that motivated this
ticket was a hand-rolled `gh run list` / `gh run view --job` / `gh api
.../logs` shell-out, eyeballed by an operator or an agent. That cost real
time and produced real errors -- three uncorrelated calls per status check,
an EMPTY log returned for a job that had genuinely failed with no way to
tell that apart from a clean run, and a ~100-failure cluster mis-attributed
to the wrong platform because a cancelled run's truncation was invisible.

This module is PART 1 of the T-2982 epic only: the seam and its failure
modes. Structured CI reporting (parsing runs/jobs/steps/failures into
clustered records, T-2984) and CI-result validity against the obligation
graph (T-2985) are deliberately NOT built here -- they sit on top of this
seam, they are not part of it.

## Error types

`GhError` (an `ErrorSet`, see `~/.claude/refs/typani.md`) names every
failure mode a `frob.ghio` function can hand back:

- `NotInstalled` -- `gh` is not on PATH.
- `NotAuthenticated` -- `gh auth status` failed (no credentials at all).
- `CredentialsExpired` -- distinct from `NotAuthenticated`: the remedy is
  `gh auth refresh`, not `gh auth login` from scratch.
- `NoRemote` -- no GitHub remote configured, or the repo is not on GitHub
  at all. frob must stay useful off-GitHub (the same portability doctrine
  PLATFORM001 enforces for OS-specific paths) -- every caller of this
  module MUST treat `NoRemote` as a normal, expected outcome, not an
  error to surface loudly.
- `RateLimited` -- distinct from `NetworkUnreachable`: the remedy differs
  (wait out the window vs. check connectivity).
- `NetworkUnreachable`.
- `NotFound` -- an unknown run or job id.
- `EmptyLog` -- log retrieval succeeded (no subprocess error) but
  returned zero bytes for a job that did NOT succeed. This is the
  measured 2026-08-25 incident (`--log-failed` returning nothing for a
  genuinely failed job): never handed back as a clean `Ok("")` as if
  there were nothing to report.
- `RunInProgress` -- `gh run view --log` refuses while the parent RUN is
  still in progress, even for a JOB that has already completed. Mapped
  here rather than left as an opaque `GhFailed` since `job_log` avoids
  hitting this by routing through the job-scoped `gh api` route instead
  (see below) -- callers that hit it anyway (e.g. calling `gh run view
  --log` directly, outside this seam) get a named reason.
- `GhFailed` -- any `gh` failure this module's stderr classifier could
  not place into a more specific bucket above. Logged at WARNING with the
  unclassified stderr excerpt so a real new mode can be added to the
  classifier later rather than staying permanently generic.

## Data models

- `GhEnvironment` -- `preflight`'s result: gh's version string and the
  resolved `owner/repo` account string.
- `RunSummary` -- one row of `gh run list`.
- `JobSummary` -- one job belonging to a run.
- `RunDetail` -- a run plus every job it contains, from one `gh run view`
  call.
- `JobLog` -- a job's log text plus two explicit booleans, `empty` and
  `truncated`, so a caller never has to infer either from string content:
  - `empty=True`: the call succeeded with zero bytes returned, and the
    owning job's own status did not indicate failure (nothing to
    distinguish -- this is a genuinely clean/no-log-needed case,
    returned as `Ok`, not `Err(EmptyLog)`).
  - `truncated=True`: the OWNING RUN was cancelled. The log text exists
    but may end before a failure summary (e.g. pytest's) was ever
    written -- its presence is not evidence the failures it caused are
    captured in it.

## Public API

- `preflight(root) -> Result[GhEnvironment, GhError]` -- classifies
  whether `gh` is usable at all under `root` (installed, authenticated,
  has a GitHub remote) before any call that reaches GitHub proper is
  attempted.
- `list_runs(root, *, limit=20, workflow=None) -> Result[tuple[RunSummary, ...], GhError]`.
- `view_run(root, run_id) -> Result[RunDetail, GhError]` -- one run plus
  its jobs in a single `gh run view --json` call.
- `job_log(root, run_id, job_id) -> Result[JobLog, GhError]` -- the
  measured-safe way to fetch one job's log. Routed through the
  job-scoped REST route (`gh api repos/{owner}/{repo}/actions/jobs/
  {job_id}/logs`), NOT `gh run view --log`/`--log-failed`, per the
  2026-08-25 measurements this ticket encodes:
  - `gh run view --log` refuses while the parent run is still in
    progress, even for a job that has already completed
    ("run <id> is still in progress; logs will be available when it is
    complete").
  - The job-scoped `gh api .../logs` route succeeds for a completed job
    while its run is still going (measured: 78KB and 109KB retrievals),
    and returns a genuine HTTP 404 only if the job itself is still in
    progress -- mapped to `GhError.NotFound`.
  - A cancelled run's log is retrievable but may be truncated before a
    failure summary was ever written -- surfaced via `JobLog.truncated`,
    never silently.

## Testing without `gh`

`gh` is not guaranteed to be installed or authenticated in every
environment this repo's tests run in, so every test in
`tests/test_ghio.py` fakes the subprocess boundary the way
`tests/test_gitio.py` does for git: `monkeypatch` `frob.ghio.run_argv`
(the one seam this module spawns through, itself `frob.gitio`'s own
public spawn primitive) to return a scripted `ProcResult` rather than
actually invoking `gh`. Every named `GhError` mode above has at least one
test that produces it, plus a must-not-crash case exercising the full
"no gh, no auth, no GitHub remote" path end to end -- `preflight` and
every other public function must return `Err(...)` values, never raise,
in that environment.

## frob:doc coverage

Every public symbol in `src/frob/ghio.py` carries a `frob:doc
docs/modules/ghio.md#<anchor>` directive pointing at this file, per the
doc-graph discipline `frob check`'s DOC gates enforce elsewhere in this
repo.
