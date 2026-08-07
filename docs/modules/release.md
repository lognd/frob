# frob.release -- mechanical semver from the public-API graph

One sentence: the graph already knows every public symbol's signature
digest, so `frob release` computes the correct version-bump class instead
of leaving it to judgment, and the REL001 gate fails a release whose
declared version does not cover the observed public-API change.

**`.frob-release.json` is the ONE version authority (T-1009).**
`pyproject.toml`'s `[project].version`, `uv.lock`'s own `version` line, and
CHANGELOG.md's heading entries are all DERIVED artifacts -- `frob release
sync` regenerates all three from the manifest's `version` field. Never edit
a derived artifact's version by hand; edit `.frob-release.json` (or let
`frob ticket land`'s REL001 bump write it) and run `sync`. The REL002 gate
(below) catches a hand-edit the moment it happens.

## The bump classes

| Change | Class | Example |
|---|---|---|
| a public signature removed or changed | MAJOR | `def f(x)` -> `def f(x, y)`, or `f` deleted |
| a new public symbol added | MINOR | a new public function/class |
| only bodies/docs changed | NONE (patch by choice) | refactor with no API change |

"Public" excludes test code and leading-underscore/dotted-private symbols.

## Workflow

<!-- frob:describes src/frob/release/__init__.py::stamp -->
<!-- frob:describes src/frob/release/__init__.py::diff_class -->
```bash
frob release stamp     # at release time: record the public API + version
                       # into the tracked .frob-release.json manifest
frob release check     # verify the current version bump covers the change
frob release sync      # T-1009: regenerate pyproject.toml/uv.lock/CHANGELOG.md
                       # from .frob-release.json's authoritative version
```

`stamp` writes `.frob-release.json` (tracked source of truth: `{version,
api}` where `api` maps each public symref to its signature digest). `check`
rebuilds the graph, diffs the current public API against the manifest,
classifies the change, and reports the minimum acceptable version. `sync`
(T-1009) reads the manifest's `version` and rewrites `pyproject.toml`'s
`version = "..."` line, re-runs `uv lock`, and inserts a `## [version] -
unreleased` CHANGELOG.md skeleton entry if one does not already exist --
the same three artifacts `frob ticket land`'s REL001 bump callback keeps in
sync at land time, now available as a standalone command (also what `make
upload` runs after `frob release stamp`).

## REL001 gate

<!-- frob:describes src/frob/gates/__init__.py::release_gate -->

REL001 runs inside `frob check` (and `frob check --only release`). It is
**opt-in**: it does nothing until a `.frob-release.json` manifest exists,
so a repo adopts the discipline by running `frob release stamp` once. It
fails when:

- the public API changed since the manifest by a class the declared
  `[project].version` does not cover (message names the required minimum,
  e.g. "bump to >= 2.0.0"), or
- the API changed but `CHANGELOG.md` (if present) has no entry naming the
  current version.

After a legitimate release, re-run `frob release stamp` to move the
baseline forward.

## REL002 gate (T-1009)

<!-- frob:invariant INV-044 -->
<!-- frob:describes src/frob/gates/__init__.py::_rel002_coherence_violations -->

REL002 runs alongside REL001 inside the same `release` check stage (`frob
check --only release`), unconditionally -- unlike REL001's bump/changelog
half, it is NOT suppressed under `FROB_AGENT` or land-ownership, since a
coherence mismatch is a bug the instant it exists, not a land-time step.
It compares `.frob-release.json`'s `version` (the ONE authority) against
`pyproject.toml`'s `[project].version` and `uv.lock`'s own package-version
entry, and reports a single `ERROR`-severity finding naming every
disagreeing artifact when any differs -- `frob release sync` is the fix.
Born `ERROR` from a clean baseline (no config graduation needed, DOC007
precedent): a repo that has actually run `sync` has zero disagreements.

## Public API

<!-- frob:describes src/frob/release/__init__.py::BumpClass -->
<!-- frob:describes src/frob/release/__init__.py::ReleaseManifest -->
<!-- frob:describes src/frob/release/__init__.py::ReleaseError -->
<!-- frob:describes src/frob/release/__init__.py::manifest_path -->
<!-- frob:describes src/frob/release/__init__.py::load_manifest -->
<!-- frob:describes src/frob/release/__init__.py::stamp -->
<!-- frob:describes src/frob/release/__init__.py::diff_class -->
<!-- frob:describes src/frob/release/__init__.py::required_version -->
<!-- frob:describes src/frob/release/__init__.py::satisfies -->
<!-- frob:describes src/frob/release/__init__.py::set_manifest_version -->

`BumpClass` is the ordered semver change class (`NONE < PATCH < MINOR <
MAJOR`). `ReleaseManifest` is the pydantic model persisted to
`.frob-release.json` (`version` + `api` symref-to-digest map).
`ReleaseError` is the `ErrorSet` of fallible outcomes (`NoManifest`,
`Malformed`, `BadVersion`, `WriteFailed`). `manifest_path` resolves the
tracked manifest path under a repo root. `set_manifest_version` (T-1078)
rewrites ONLY the manifest's `version` field in place, preserving its
recorded `api` map -- `frob.tickets._land`'s write-side guarantee that a
REL001 bump's `.frob-release.json` stays coherent with
`pyproject.toml`/`CHANGELOG.md` in the same land step, regardless of what
a `bump_version` callback did or forgot to do.

**Every write this module performs is crash-safe (T-1359).** `stamp`,
`set_manifest_version`, and `rewrite_pyproject_version` all route their
disk write through a shared `_atomic_write_release` helper that delegates
to `frob.tickets._store.atomic_write` (temp file + `fsync` + `os.replace`)
-- the same half-written-file hazard class T-1348 already closed for
`frob.gates._fix_engine`'s direct writes. A write failure surfaces as
`Err(ReleaseError.WriteFailed)` with the original file left intact,
instead of a bare `Path.write_text` that could leave a truncated
`pyproject.toml`/`.frob-release.json` if the process died mid-write.
`changelog_skeleton_entry` uses the same primitive but keeps its existing
`bool` contract (no error channel) -- a write failure there logs and
reports `False` ("nothing changed"), matching
`frob.gates._fix_engine._write_text`'s T-1348 posture rather than
widening every caller's signature.

```python
class BumpClass(IntEnum):        # NONE = 0, PATCH = 1, MINOR = 2, MAJOR = 3
    ...

class ReleaseManifest(BaseModel):
    version: str
    api: dict[str, str]

class ReleaseError(ErrorSet):
    NoManifest
    Malformed
    BadVersion
    WriteFailed          # T-1359: crash-safe write to a release-owned file failed

def manifest_path(root) -> Path
def load_manifest(root) -> Result[ReleaseManifest, ReleaseError]
def stamp(root, snapshot, version) -> Result[str, ReleaseError]
def set_manifest_version(root, version) -> Result[str, ReleaseError]
def diff_class(manifest, snapshot) -> BumpClass         # NONE|PATCH|MINOR|MAJOR
def required_version(previous, bump) -> Result[str, ReleaseError]
def satisfies(current, minimum) -> bool
def rewrite_pyproject_version(root, version) -> Result[bool, ReleaseError]
def changelog_skeleton_entry(root, version, note=None) -> bool
```

## Stamp refuses an un-bumped API change (T-1381)

`stamp` rebaselines the recorded public API at whatever version is current.
That makes running it ALONE a footgun: REL001's remedy reads "bump the
version to >= X, then run: frob release stamp", and the stamp half silences
the gate on its own while the release never happens.

So `stamp` now runs REL001's own computation -- `diff_class` against the
recorded manifest, then `required_version` -- and returns
`Err(ReleaseError.UnbumpedApiChange)` when the current version falls short,
writing nothing at all. A partial write would rebaseline the very API it
just rejected.

Two cases deliberately pass through: a first-ever stamp (no manifest to be
short of) and an already-adequate version. `--allow-unbumped`
(`stamp(..., allow_unbumped=True)`) is the explicit, justification-required
override, matching `--skip-mutation-evidence` and `--allow-cross-ticket`.

### `--allow-unbumped` requires a reason and is audited (T-1768)

`--allow-unbumped` used to bypass the refusal above silently: no
`--reason` flag existed, nothing was logged beyond the flag's own help
text, and nothing was recorded. That made it the worst of the
`--force`-shaped bypass family T-1762 closed for `ticket archive --force`
and `ticket land --finish --force` -- those two skip a guard for ONE
invocation; `--allow-unbumped` PERMANENTLY rebaselines `.frob-release.json`,
silently redefining what counts as an API change from that moment
forward, and a manifest rewrite looks like any other manifest rewrite in
the diff.

`stamp(..., allow_unbumped=True, reason=...)` now mirrors T-1762's landed
remedy exactly:

- When `allow_unbumped=True` actually bypasses a real shortfall (the same
  `_bump_shortfall` computation above found one), a non-blank `reason` is
  REQUIRED -- `Err(ReleaseError.UnbumpedReasonMissing)` otherwise, nothing
  written. `allow_unbumped=True` with NO real shortfall (the version
  already covers the change) is still a no-op guard-wise and demands no
  reason -- nothing was actually bypassed, the same posture `frob ticket
  archive --force` with no live lease already established.
- The bypass appends one `ForceOverrideEntry` line to the repo-root
  `force-overrides.jsonl` (`frob.tickets._force_override.
  record_force_override`, the SAME audit-record shape `ScopeChangeEntry`/
  `AckAuditEntry`/`EvidenceChangeEntry` already use elsewhere, not a fifth
  one) naming the version move, the bump class that was skipped, and the
  count of symbol digests that changed (`_changed_symbol_count`) -- so the
  record says not just THAT the baseline moved but roughly how much
  surface it silently accepted.
- It logs at WARNING naming the old version, the new version, the skipped
  bump class, and the reason -- a bypass nobody can see is
  indistinguishable from the guard not existing.

`frob release stamp --allow-unbumped` takes the matching `--reason TEXT` /
`--reason-file PATH` CLI flags (`--reason-file` wins if both are given,
read verbatim -- T-0737's shell-injection-avoidance precedent).

Deliberately NOT done: a name-pattern gate for override-shaped flags in
general. T-1762 examined that and rejected it -- `--skip-gates` appears in
both the needs-a-reason and correctly-free camps, so the distinction is
semantic, not lexical, and a name-based rule would false-positive on
every `frob check --skip-*` flag while still requiring a human to read
each new one.

The write itself (once the un-bumped check clears) goes through the same
crash-safe `_atomic_write_release` primitive as every other write in this
module (T-1359, see Public API above) -- `Err(ReleaseError.WriteFailed)`
on the should-never-happen I/O failure path, original manifest untouched.

## Design notes

- **Manifest is tracked text; the graph is derived.** The baseline lives in
  git so a release's API surface is reviewable in the diff.
- **Signature digests, not bodies.** REL001 keys on `sig` digests -- a body
  refactor is not a breaking change, which is exactly semver's contract.
- **Opt-in, not on by default.** Like `[gates.severity]`, a repo turns the
  release discipline on deliberately; unstamped repos are unaffected.
- **PEP440 pre-release suffixes are tolerated** (parsed to X.Y.Z); the
  bump comparison ignores the suffix. Full PEP440 ordering is future work.
