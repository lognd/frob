# Release: publishing `frob`, `frob-core`, and `strata-core` (T-3011)

frob ships three separately-published artifacts:

- `frob` -- pure Python, setuptools-built, `uv build --wheel`.
- `frob-core` -- PyO3/`abi3-py311` extension (frob.dup R3+ clone-detection
  kernels), maturin-built.
- `strata-core` -- PyO3/`abi3-py311` extension (frob.strata closure/
  staleness/demand kernels), maturin-built.

`abi3-py311` collapses the Python-version axis to ONE wheel per platform
(not one per CPython minor version), so the target matrix is small:
manylinux x86_64, manylinux aarch64, macOS x86_64, macOS arm64, Windows
x86_64 -- five platform wheels per crate, plus one sdist per crate.

## Workflow structure (`.github/workflows/release.yml`)

Three jobs:

1. **`build`** (+ `build-sdists`) -- runs on every manual dispatch
   (`workflow_dispatch`), no approval needed. A `maturin-action`-based
   matrix builds `frob-core` and `strata-core` wheels for all five targets
   plus their sdists, and a plain `uv build` step builds the pure-Python
   `frob` wheel + sdist. Everything is uploaded as a CI artifact
   (`actions/upload-artifact`) and retained -- this is the "prove it
   works, keep the evidence" half, and it is NEVER gated on approval.
2. **`verify-ci-status`** (T-3251) -- runs on every manual dispatch, no
   approval needed either; see [below](#verify-ci-status) for what it
   checks and why it exists as a fourth gate alongside the three T-3011
   gates, not a replacement for any of them.
3. **`upload`** -- `needs: [build, build-sdists, verify-ci-status]`,
   targets the `pypi` GitHub Environment, which has a required reviewer
   configured in the repo's environment protection rules. GitHub will not
   start this job until a human with reviewer access clicks Approve on
   that specific run -- the approval is recorded on the run itself, not
   merely a runbook convention. This job downloads the `build` job's
   artifacts and runs `pypa/gh-action-pypi-publish` using PyPI **trusted
   publishing** (OIDC: `id-token: write` permission, no stored PyPI
   token) against each of the three package indices.

The `on:` block declares `workflow_dispatch` ONLY -- no `push`, no `tags`,
no `pull_request`, no `release` trigger. There is structurally no event
that starts this workflow other than a human choosing "Run workflow" in
the Actions UI. `ci.yml` (push/PR triggered) is a completely separate
workflow file that never touches `upload` or the `pypi` environment.

### Why this is a structural gate, not a convention

- No automatic trigger reaches `release.yml` at all -- a tag push, a merge
  to `main`, or a scheduled cron cannot invoke it, because none of those
  events is listed under `on:`.
- Even a manual dispatch of `release.yml` only ever runs `build`. `upload`
  additionally requires the `pypi` environment's required-reviewer gate,
  enforced by GitHub itself (not by anything in the workflow YAML that an
  agent or a careless edit could route around) -- the workflow file
  declares the requirement (`environment: pypi`), and the actual
  enforcement lives in the repository's Settings > Environments
  configuration, which only a repo admin can change.
- `build` and `upload` are separate jobs with separate log output, so
  "wheels got built and retained" and "wheels got uploaded to PyPI" are
  two independently observable facts on every run -- the acceptance-test
  proof (see below) is reading exactly this distinction off a real run.

### Proof: a normal push does not upload

`release.yml` declares only `workflow_dispatch` under `on:`, and `ci.yml`
(the workflow that DOES run on every push/PR) contains no reference to
`release.yml`, the `pypi` environment, or `gh-action-pypi-publish`
anywhere in it. A push to `main` or a PR therefore cannot reach the
`upload` job by any path -- there is no trigger connecting them. This is
checked mechanically, not just asserted in prose: `tests/unit/
test_release_workflow_gate.py` parses both workflow files and fails the
build if `release.yml` ever gains a `push`/`pull_request`/`schedule`/
`release` trigger, or if `upload` ever loses its `environment: pypi`
gate or its `needs: build` dependency.

<a id="version-coupling-t-3011"></a>
## Decision 1: version coupling (`==`, all three, cut together)

`frob`, `frob-core`, and `strata-core` are pinned to the exact same
version string, always. `frob`'s own `pyproject.toml` declares:

```toml
[project.optional-dependencies]
native = ["frob-core==<X.Y.Z>", "strata-core==<X.Y.Z>"]
```

and `frob-core/pyproject.toml` / `strata-core/pyproject.toml` each declare
`version = "<X.Y.Z>"` matching the same string. `frob.gates.
_version_coupling.version_coupling_gate` (rule `VERSION001`) reads all
three `pyproject.toml` files and fires an ERROR-severity violation if any
of the following is true:

- the `native` extra is missing an exact pin for either crate;
- a pin exists but is not an exact `==` specifier (a `>=`/`~=`/unbounded
  pin is rejected outright, not just discouraged);
- a pin's version does not match `frob`'s own `[project].version`;
- `frob-core/pyproject.toml` or `strata-core/pyproject.toml`'s own
  `version` field does not match `frob`'s.

**Why exact pins, not a compatible range:** this repo already paid for
the "version strings alone are not enough to detect skew" lesson once --
T-2884 had to add a git-SHA check to a daemon because two things that were
supposed to move together did not, and version numbers alone could not
prove it. A native PyO3 extension is less forgiving than that daemon case:
a Python-side change that assumes a new Rust-side field or behavior,
loaded against an OLDER (or simply DIFFERENT) compiled `frob_core`/
`strata_core`, does not raise `ImportError` -- it silently returns wrong
answers or silently drops a field the Rust side has no code for. A loose
pin (`frob-core>=0.5`) lets pip resolve to ANY compatible-by-number
version at install time, defeating the "all three cut together" release
discipline the moment someone else's environment resolves dependencies
independently. Exact `==` on a version string that is bumped in lockstep,
enforced by a gate that runs in `frob check` on every commit (not merely
recommended in this document), is the only shape that catches skew before
it reaches an adopter's machine rather than after.

A residual gap, disclosed rather than silently left: today's release cut
requires a human (or `frob ticket land`, in a follow-up) to bump all three
`version` fields together by hand -- `VERSION001` catches the skew if that
step is missed, but does not perform the bump itself. Automating the
three-file bump into `frob ticket land`'s existing REL001 release
machinery is out of this ticket's scope (`src/frob/tickets/_land_release.py`
carries other tickets' scope) and is filed as a follow-up.

<a id="native-acceleration-degrade-doctrine-t-3011"></a>
## Decision 2: no wheel matches -> degrade loudly, never build from source

An sdist fallback would make `pip install frob-core`/`strata-core` build
from source when no prebuilt wheel matches the install target, requiring a
Rust toolchain on a machine that almost certainly does not have one -- a
miserable first run for exactly the adopter this whole effort exists to
serve. `frob`'s own CI already proves the alternative works: the
`standalone-install` job in `ci.yml` builds the bare `frob` wheel (no
native extras at all) and proves it installs and runs cleanly in ~15s.

The chosen behavior instead is the PLATFORM001 doctrine (`docs/modules/
gates.md`'s guard-loudness rule) applied to distribution: **declare the
boundary, never degrade silently.** `frob.doctor.native_degrade_warning`
checks `frob_core`/`strata_core` importability and, when either is
missing, returns a one-line message naming BOTH missing extensions by
name and pointing at the exact fix -- `pip install 'frob[native]'` for an
installed package, or `make core` for a source checkout (distinguished by
whether `frob-core/Cargo.toml` exists under the repo root). `__main__.
_print_startup_warnings` prints this on every subcommand invocation
(alongside the existing stale-binary and Claude-config-drift warnings),
not only on an explicit `frob doctor` run -- an adopter who never thinks
to run `frob doctor` still sees it on their very first `frob check`.

This is a MUST-FIRE fixture, not an incidental log line:
`tests/unit/test_doctor.py::TestNativeDegradeWarning.
test_missing_extensions_named_loudly` monkeypatches both extensions to
"not importable" and asserts the returned message names both
`frob_core` and `strata_core` explicitly; a companion test asserts the
function returns `None` (no message at all) when both import cleanly, so
a regression that makes this fire on the common, fully-accelerated path
would also fail loudly.

## Decision 3: PyPI trusted publishing (OIDC), not a stored token

`upload` uses `pypa/gh-action-pypi-publish` with `permissions: id-token:
write` and no `password`/token input -- PyPI's trusted-publisher OIDC
exchange authenticates the specific GitHub Actions workflow run (repo +
workflow file + environment) directly with PyPI, so there is no
long-lived API token sitting in repository secrets that could leak,
outlive its need, or be reused outside this one workflow's `upload` job.
Each of the three PyPI/TestPyPI project pages needs its trusted publisher
configured to name this repo, `release.yml`, and the `pypi` environment
before the first real publish -- a one-time, owner-performed setup step
tracked separately from this ticket (it requires an existing PyPI project
to attach the publisher to, which itself requires the first publish's
approval this ticket is explicitly NOT authorized to give).

<a id="verify-ci-status"></a>
## Decision 4: `verify-ci-status` -- CI must be green for THE RELEASED COMMIT (T-3251)

Before T-3251, nothing in `release.yml` checked that the commit being
released had a green CI run. `upload`'s `needs: [build, build-sdists]`
only proves wheels built and imported on each platform -- not that the
test suite passed, `frob check` was clean, or the CI matrix was green. A
human could dispatch a release from a red `main` and every existing gate
would say yes. A PyPI upload is irreversible (a version number cannot be
reused, even after a yank), so this was the one workflow in the repo
where a bad run could not be fixed by a follow-up commit.

`verify-ci-status` closes that gap as a FOURTH gate, added alongside
T-3011's three (manual-dispatch-only trigger, `needs: build`, the `pypi`
environment's required reviewer) -- none of those three was weakened or
replaced to add this one.

**What it checks.** `scripts/verify_release_ci_status.py` (unit-tested in
`tests/unit/test_verify_release_ci_status.py`, no real `gh` binary or
network access needed) queries `gh api repos/<owner>/<name>/actions/
workflows/ci.yml/runs?head_sha=<sha>` for `github.sha` -- THE EXACT COMMIT
being released, resolved by SHA, never by branch name and never "the most
recent run" on any commit. A run on a different commit passing is never
read as this commit passing.

**Three distinct outcomes, never collapsed into two:**

- **GREEN** -- the matching run is `status=completed`,
  `conclusion=success`. The step exits 0; `upload` proceeds to its own
  separate `pypi` environment approval gate, unchanged.
- **RED** -- the matching run completed with any other conclusion
  (`failure`, `cancelled`, `timed_out`, ...). The step exits 1;
  `upload` is skipped via `needs:`.
- **UNDETERMINED** -- the `gh api` call itself failed, returned
  unparseable JSON, found no run for this exact SHA, or found one still
  `in_progress`/`queued`. Fails CLOSED exactly like RED: an unreadable
  status is never treated as green. This repo's own dominant defect
  class is a failed measurement reported as a successful one, and a
  release is the worst possible place to repeat it.

**The override.** `workflow_dispatch` declares two inputs:
`override_red_ci` (boolean, default `false`) and `override_reason`
(string, default `""`). A RED or UNDETERMINED status is refused UNLESS
`override_red_ci=true` AND `override_reason` is non-empty -- an override
request with no reason is refused exactly like no override at all. The
override is never the default, and the run's own log (via
`github.actor`, already recorded on every workflow run, plus the printed
`override_reason`) is the audit trail for who set it and why -- no
separate approval mechanism was added for this, since `upload`'s own
`pypi` environment reviewer gate still runs afterward regardless.

## Sequencing: build now, first publish gated on green + consent

As of this ticket there is no verified green CI run on any platform
(Windows ~19 test failures across 7 files, macOS ~144 uncharacterised
failures, Linux never producing a verified green full-suite baseline --
see T-3003/T-2930/T-2971/T-2992). `release.yml` is ready to run today and
will build and retain real wheels on a manual dispatch, but the FIRST
actual publish requires BOTH of the following, independently:

1. a verified green CI run across the full matrix (Linux, macOS,
   Windows), and
2. explicit owner approval recorded via the `pypi` environment's
   required-reviewer gate for that specific run.

Neither gate substitutes for the other. This ticket builds the machinery
and proves the consent gate is structural; it does not publish anything,
and no PyPI or TestPyPI upload was performed as part of landing it.
