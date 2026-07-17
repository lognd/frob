# frob.release -- mechanical semver from the public-API graph

One sentence: the graph already knows every public symbol's signature
digest, so `frob release` computes the correct version-bump class instead
of leaving it to judgment, and the REL001 gate fails a release whose
declared version does not cover the observed public-API change.

## The bump classes

| Change | Class | Example |
|---|---|---|
| a public signature removed or changed | MAJOR | `def f(x)` -> `def f(x, y)`, or `f` deleted |
| a new public symbol added | MINOR | a new public function/class |
| only bodies/docs changed | NONE (patch by choice) | refactor with no API change |

"Public" excludes test code and leading-underscore/dotted-private symbols.

## Workflow

```bash
frob release stamp     # at release time: record the public API + version
                       # into the tracked .frob-release.json manifest
frob release check     # verify the current version bump covers the change
```

`stamp` writes `.frob-release.json` (tracked source of truth: `{version,
api}` where `api` maps each public symref to its signature digest). `check`
rebuilds the graph, diffs the current public API against the manifest,
classifies the change, and reports the minimum acceptable version.

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

## Public API

<!-- frob:describes src/frob/release/__init__.py::stamp -->
<!-- frob:describes src/frob/release/__init__.py::diff_class -->
<!-- frob:describes src/frob/release/__init__.py::required_version -->

```python
def stamp(root, snapshot, version) -> Result[str, ReleaseError]
def load_manifest(root) -> Result[ReleaseManifest, ReleaseError]
def diff_class(manifest, snapshot) -> BumpClass         # NONE|PATCH|MINOR|MAJOR
def required_version(previous, bump) -> Result[str, ReleaseError]
def satisfies(current, minimum) -> bool
```

## Design notes

- **Manifest is tracked text; the graph is derived.** The baseline lives in
  git so a release's API surface is reviewable in the diff.
- **Signature digests, not bodies.** REL001 keys on `sig` digests -- a body
  refactor is not a breaking change, which is exactly semver's contract.
- **Opt-in, not on by default.** Like `[gates.severity]`, a repo turns the
  release discipline on deliberately; unstamped repos are unaffected.
- **PEP440 pre-release suffixes are tolerated** (parsed to X.Y.Z); the
  bump comparison ignores the suffix. Full PEP440 ordering is future work.
