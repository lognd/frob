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

**What "green" means as of T-3425.** `ci.yml`'s `build` job runs `windows-latest` as an ADVISORY leg (`continue-on-error: true`) until T-3076's 278 Windows-only failures (five missing POSIX primitives) are drained -- see `docs/design/windows-portability.md`. The windows-latest job still runs and reports on every push (its signal is not discarded), but a windows-latest failure no longer flips `ci.yml`'s overall conclusion, and so no longer flips what `verify_release_ci_status.py` reads as GREEN for this workflow. GREEN as measured here is `ubuntu-latest` and `macos-latest` passing; a red windows-latest leg is a known, tracked gap, not silently ignored. Re-tighten this note (and `override_red_ci`'s framing above) once T-3076 reaches zero and the advisory flag is removed.

## Sequencing: build now, first publish gated on green + consent

As of T-3254 (2026-08-28), Linux has a verified full-suite baseline
(T-2992: 12,039 collected, 86 real failures, triaged into seven tickets --
T-3019/T-3033/T-3034/T-3035/T-3037/T-3040/T-3041 -- all seven now `[done]`
on main). Windows and macOS status has NOT been re-measured under this
ticket; do not assume it matches the Linux number. Before a real cut,
re-check the live CI runs for all three platforms rather than trusting
this paragraph -- it is a snapshot, not a gate. (T-3251 is building the
mechanical gate that refuses `upload` against a commit without a green
per-SHA CI conclusion on every platform; until that lands, "green matrix"
below is verified by a human reading the Actions UI.)

`release.yml` is ready to run today and will build and retain real wheels
on a manual dispatch, but the FIRST actual publish requires BOTH of the
following, independently:

1. a verified green CI run across the full matrix (Linux, macOS,
   Windows), and
2. explicit owner approval recorded via the `pypi` environment's
   required-reviewer gate for that specific run.

Neither gate substitutes for the other. T-3011 built the machinery and
proved the consent gate is structural; it did not publish anything, and
no PyPI or TestPyPI upload was performed as part of landing it. T-3254
adds the ordered cut procedure below; it likewise does not publish
anything and does not bump the version.

## The release-cut procedure (T-3254)

Two preconditions gate the FIRST publish (green matrix, owner approval,
above). This section places the steps AROUND those two gates -- most
importantly, where the version bump goes. `frob release check` reads the
live public-API graph and compares it against the digest stamped in
`.frob-release.json`, so **every land that touches the public API
re-invalidates the stamp**. Bumping and stamping is therefore the LAST
thing done before a cut, against the exact commit being released, never
prep work done in advance. A version bumped early and then followed by
more lands will be stale again by cut time, and `frob release check` will
say so.

<a id="do-not-use-release-publish-yet"></a>
### Known gap: `frob release publish` / `make upload` bumps the wrong thing

Do **not** run `frob release publish` (equivalently `make upload`) to
perform a real cut yet. It unconditionally bumps only the PATCH
component (`X.Y.Z -> X.Y.(Z+1)`, `next_patch_version` /
`bump_patch_version`) and then stamps, syncs, commits, pushes, builds,
and publishes against that patch-bumped version. It does not consult
`diff_class`/`required_version` at all. Verified against this repo's own
state (2026-08-28): `frob release check` says the change since the last
stamp is MAJOR-class, requiring `>= 0.531.0` from `0.530.0` (the
0.x-series MINOR-position bump semver-zero implies -- see
[Decision 1](#version-coupling-t-3011) and `required_version` in
`docs/modules/release.md`). `frob release publish`'s unconditional patch
bump would instead produce `0.530.1`, which does NOT satisfy
`>= 0.531.0` -- the command would commit, push, build, and attempt to
publish a version that fails its own repo's release gate. This is filed
as **T-3337** (out of this ticket's `docs/guides/release.md`-only scope;
the fix belongs in `src/frob/release/_publish.py`). Until T-3337 closes,
follow the manual steps below instead of `make upload`.

### Ordered steps, main is green -> wheels uploaded

Run every command from the repo root, against the exact commit that will
be released (note its SHA before starting -- step 8's dispatch and any
later tag both refer back to it):

1. **Freeze.** Stop landing tickets that touch the public API against
   `main`. Record the commit SHA you are about to cut.
2. **Confirm the two preconditions independently**: the CI matrix is
   green on that SHA for Linux, macOS, and Windows (read the Actions UI
   directly until T-3251's per-SHA gate exists), and the owner has agreed
   this SHA should ship.
3. **Compute the required version.**
   ```
   frob release check
   ```
   Reads `since <stamped>: <class> change -> need >= <X.Y.Z> (...)`. That
   `<X.Y.Z>` (or higher) is the version you bump to -- never a smaller or
   cosmetic number (see [Decision 1](#version-coupling-t-3011): the owner
   already decided against renumbering).
4. **Bump all three `version` fields to that number, by hand**, keeping
   them identical (no tool currently writes an arbitrary target version
   across all three -- see the gap above): `pyproject.toml`'s
   `[project].version`, the `native` extra's two pins
   (`frob-core==<X.Y.Z>`, `strata-core==<X.Y.Z>`), `frob-core/
   pyproject.toml`'s `version`, and `strata-core/pyproject.toml`'s
   `version`.
5. **Stamp**, against the now-bumped `pyproject.toml` and the frozen
   commit's live API graph:
   ```
   frob release stamp
   ```
   This writes `.frob-release.json`'s `version` (from the file you just
   edited) and `api` (from the current graph) together -- doing this
   before step 4 would stamp the OLD version.
6. **Sync the derived artifacts**:
   ```
   frob release sync
   ```
   Regenerates `uv.lock` and inserts the `CHANGELOG.md` skeleton heading
   for the new version if one is not already present (this repo already
   carries a `## [0.531.0] - unreleased` heading pre-written -- confirm
   its content is accurate rather than leaving it as a placeholder).
7. **Verify all three version-bearing artifacts agree, mechanically**:
   ```
   frob check --only release
   ```
   This runs REL001 (declared version covers the API change AND
   `CHANGELOG.md` names the current version) and REL002 (`.frob-
   release.json`, `pyproject.toml`, and `uv.lock` agree) together. It
   MUST exit 0 before continuing. Today (pre-bump) it does not -- that is
   this ticket's own reproduction case, and is expected to still fail
   until steps 3-6 are actually performed at a real cut.
8. **Commit and push** `pyproject.toml`, `frob-core/pyproject.toml`,
   `strata-core/pyproject.toml`, `uv.lock`, `CHANGELOG.md`, and
   `.frob-release.json` together as one `chore(release): bump to
   <X.Y.Z>` commit on `main`. This is now the commit that gets released;
   if CI has to re-run on it, re-confirm precondition 2 before continuing
   -- a version-bump commit is still a commit, and this repo does not
   exempt release commits from the green-CI requirement.
9. **Dispatch** `release.yml` (`workflow_dispatch`, manual, from the
   Actions UI or `gh workflow run`) against that exact commit. The
   `build` job runs unconditionally and retains wheels/sdists as CI
   artifacts -- no approval needed for this half.
10. **Owner approval.** The owner reviews the retained build artifacts
    and approves the `pypi` environment's required-reviewer gate for
    that specific run. `upload` then runs, publishing all three packages
    via OIDC trusted publishing (no stored token).
11. **Tag, after upload succeeds -- never before.** This repository has
    never had a git tag (`git tag` returns nothing as of T-3254). The cut
    DOES create one: after `upload` completes successfully, the owner
    tags the released commit (`git tag v<X.Y.Z> <sha> && git push origin
    v<X.Y.Z>`) as a historical marker of what shipped. This is a manual,
    post-hoc, owner-run step -- it is never automated into `release.yml`
    or any other workflow. `release.yml`'s `on:` block stays
    `workflow_dispatch` only (T-3011's structural gate; see "Why this is
    a structural gate, not a convention" above and
    `tests/unit/test_release_workflow_gate.py`); tagging AFTER a
    confirmed-successful publish, by a human, off of CI entirely, cannot
    reach that trigger surface. Do not reorder this step earlier: a tag
    pushed before `upload` succeeds would mark a commit as released that
    might not be.

### Follow-up filed alongside this ticket

- **T-3337** -- `frob release publish` / `make upload` always bumps only
  the patch component and never consults `diff_class`/`required_version`,
  so it can commit, push, and attempt to publish a version that fails
  this repo's own REL001 gate (reproduced above against live state:
  would produce `0.530.1` when `0.531.0` is required). Scope belongs in
  `src/frob/release/_publish.py` / `scripts/bump_version.py`, outside
  this ticket's `docs/guides/release.md`-only scope.
