# frob.vet -- dependency capability vetting (supply-chain defense)

One sentence: every dependency's source is statically scanned for the
capabilities it exercises (spawn processes, open sockets, eval code, read
env, run install hooks), the result is compared against the capabilities
you DECLARED it should have, and an undeclared capability -- or a capability
that newly appears in a version bump -- fails `frob check`.

Posture: allowlist conformance, same as every frob gate. A dependency is
not "verified okay" because a scanner found nothing; it is verified okay
because its observed capabilities match a human-reviewed declaration, and
any drift from that declaration is loud.

## Why capability diffs are the right primitive

Real supply-chain attacks (event-stream, xz-utils, the 2024-2026 npm/PyPI
waves) share one shape: a package that never needed network/exec/env
access suddenly gains it in a patch release. Point-in-time scanning
produces alert fatigue; DIFFING capabilities across versions produces
almost-zero-noise signal, because "requests does networking" is declared
once and never fires again, while "left-pad now opens a socket" fires
immediately.

## Capability taxonomy (per package, per version)

| Capability | Detected via (tree-sitter over frob.lang grammars) |
|---|---|
| exec | subprocess/os.system/exec*/CreateProcess/Command::new |
| eval | eval/exec/compile/Function()/importlib dynamic import |
| net | socket/http/urllib/reqwest/fetch/net:: usage |
| fs-write | writes outside the package's own tree/tempdirs |
| fs-read | reads local filesystem state (config loads, no mutation) -- T-0018, graphite adoption, docs/strata/selfconform.md#fs-read-fs-write |
| env | os.environ/process.env/std::env reads |
| process-control | sys.exit/os._exit/signal.signal -- process-lifecycle/signal-handling operations (T-1439: reclassified out of `env`, which they only ever shared by a kind-naming mismatch, not real environment-variable access) |
| ffi | ctypes/cffi/NAPI/unsafe extern/`importlib.machinery.ExtensionFileLoader` (T-0222: explicit compiled/native extension module loading -- a bare `import <native-module>` is scanner-invisible, so this stdlib literal is the narrow, unambiguous signal) |
| native | compiled artifacts in the wheel/crate (opaque to scanning) |
| install-hook | setup.py/build.rs/postinstall scripts containing any of the above |
| obfuscation | decode-then-eval chains, high-entropy string blobs, minified-source-in-sdist mismatch |
| embedded_code | large HTML/JS-shaped STRING LITERAL inside another language's source (T-0244: python's own grammar hides an embedded dashboard's markup/script from every needle table above) -- size + HTML/JS-signal heuristic over python `string` tree-sitter nodes; ALWAYS emitted for a region found (fail-closed), plus any typescript-needle hits over the region's own text |

`CAPABILITY_KINDS` (`src/frob/vet/_capability_registry/_kinds.py`, part of
the `_capability_registry` package since T-1420) has grown
beyond this table's rows to ~25 entries: precise connect-vs-listen and
read-vs-write variants of `net`/`env` (`net-connect`/`net-listen`/
`net.connect`/`net.listen`, `env-read`/`env-write`/`env.read`/
`env.write`), the normalized `fs` spelling of `fs-write`, `process-control`
(T-1439, split out of `env`), and the c-cpp-excused-kind vocabulary
(`sql`, `html_render`, `fetch_url`, `deserialize`, `client_storage`) also
live there -- see `docs/guides/extending/capability-registry.md` for the
full current list.

`native` and `obfuscation` are capabilities in their own right: compiled
code cannot be vetted statically and is therefore trusted only by explicit
declaration (`native = ["pydantic-core"]`); obfuscation signals are never
declarable -- they are VET004 errors, full stop.

<!-- frob:invariant INV-025 -->

## JavaScript/TypeScript: first-priority ecosystem

npm is where the attack volume is (the 2024-2026 waves ran overwhelmingly
through npm lifecycle scripts and typosquats), so the JS/TS path gets
first-class treatment, not parity:

- **package-lock.json and pnpm-lock.yaml today**; yarn.lock/bun.lockb are
  a disclosed 0.2.x addition, not yet parsed
  (`src/frob/vet/_lockfile.py`'s own module docstring).
- **Lifecycle scripts are the headline capability (rule id `VET-JS`, not
  `VET-JS001`)**: preinstall/install/postinstall/prepare in any
  node_modules package.json map to `install-hook` and are DENIED BY
  DEFAULT -- a lifecycle script needs an explicit `[vet.allow]` entry
  naming it (`src/frob/vet/_lifecycle.py`,
  `_scan._lifecycle_violations`). No separate `.npmrc`
  `ignore-scripts=true` verification exists.
- **Typosquat distance (VET-JS003)**: new dependency names within edit
  distance 1-2 of a top-N npm package (bundled list, refreshed with
  `--sync-advisories`) require explicit confirmation in [vet.allow].
- **Non-registry sources (VET-JS004)**: git/http/file dependencies in
  the manifest are declarable-only, never silent.
- **Unbuilt today**: dependency-confusion detection (a `VET-JS002`-style
  check against `[vet].internal_scopes`) is disclosed future work, not
  shipped -- `[vet].internal_scopes` is not a config key today.

## Python, Rust, C/C++: same care, ecosystem-shaped

The cross-registry campaigns (TrapDoor, May 2026: one actor, 34+ packages
across npm+PyPI+crates.io, ecosystem-specific delivery) prove the TTPs hop
registries; only the execution vehicle changes. Per-ecosystem rules target
each vehicle:

**Python (VET-PY family)** -- historic record: install-time setup.py
payloads (the dominant PyPI pattern), typosquat floods (500+ in one 2024
wave; boto3/requests variants in early 2026), torchtriton-style dependency
confusion against private indexes, account takeovers:
- VET-PY001: sdist with executable setup.py/setup.cfg cmdclass when a
  wheel exists -- prefer-wheels posture; sdist builds are install-time
  code execution and get the install-hook capability. `--only-binary`
  enforcement recommended in CI.
- VET-PY002: `.pth` files in the artifact (interpreter-startup code
  execution -- the quiet Python analog of postinstall) and import-time
  capability use at module top level (net/exec/env in module scope
  rather than inside functions).
- VET-PY003: pickle/marshal payloads in package data (also the AI-model
  vector: model files ARE pickle); serialized-code loads are `eval`.
- VET-PY004: index-priority confusion -- a name that exists on both a
  configured private index and PyPI fails until pinned to one source.

**Rust (VET-RS family)** -- build.rs runs arbitrary code at cargo build
time, before any runtime control; proc-macros execute in the compiler:
- VET-RS001: build.rs is too ubiquitous to deny outright, so its BODY is
  capability-scanned like any package code -- net/env-read/exec inside
  build.rs is high-severity and must be declared per-crate.
- VET-RS002: proc-macro crates carry a compile-time-exec capability
  requiring declaration; a version bump that ADDS a proc-macro or
  build.rs where none existed is escalation (VET003) at max severity.
- VET-RS003: [patch]/git dependencies and registry substitutions are
  declarable-only.

**C/C++ (VET-C family)** -- no central registry, so the vehicle is the
acquisition path itself: vendored tarballs, git submodules, CMake
FetchContent, conan/vcpkg:
- VET-C001: every FetchContent/ExternalProject/submodule must pin an
  exact commit hash or artifact sha -- branch/tag pins fail (tags move;
  xz taught the tarball-vs-repo lesson).
- VET-C002: vendored source diffed against the pinned upstream (VET008
  applied to vendoring); a vendored tree that matches no upstream commit
  is a violation.
- VET-C003: conan/vcpkg lockfiles treated as first-class lockfiles
  (parse, scan, escalate like any other ecosystem).

**Slopsquatting and agent-targeted attacks (VET011)** -- the 2026 CISA/
Five Eyes advisory codified what agentic workflows changed: attackers
register LLM-hallucinated package names (43% of hallucinated names repeat
across runs, making them farmable) and craft READMEs so agents RECOMMEND
their packages (LLMO abuse). frob is built for agent workflows, so this
gets its own rule: a dependency first published fewer than
`[vet].quarantine_days` ago (default 14), or with anomalously low
adoption for its claimed maturity, cannot enter the lockfile without an
explicit human-reviewed [vet.allow] entry -- an agent can propose it, but
a person admits it. Cooldown windows are the single cheapest defense
against both slopsquats and just-published compromises, and they cost
nothing for established dependencies.

The cross-ecosystem principle: capability declarations, escalation diffs,
cooldown quarantine, and obfuscation ensembles are REGISTRY-AGNOSTIC --
they are the same gate logic fed by per-ecosystem extractors, so a new
package manager is an adapter, not a redesign.

## Obfuscation detection (the VET004 ensemble)

Known technique families and their detectors -- honest caveat first: this
catalog covers the families observed in real-world npm/PyPI malware to
date, and it WILL be incomplete against tomorrow's; the ensemble is
therefore anchored on anomaly detectors (entropy, stylometry, shape) that
do not require knowing the trick, with signatures layered on top for
cheap wins. Detection is fatal, never "deobfuscate and judge intent."

| Family | Techniques | Detector |
|---|---|---|
| encoded-payload | base64/hex/charcode arrays, String.fromCharCode chains, reversed/split-join strings, zlib+b64 nesting (py) | string-literal Shannon entropy vs per-language corpus baseline; decode-call density |
| eval-reachability | eval(atob(...)), Function()/new Function, setTimeout(string), vm.runInContext, exec(compile()), __import__/importlib with computed names, marshal/pickle code loads, obj["ev"+"al"] indirect access | dataflow query: any path from a decode/concat source to a code-execution sink -- the single highest-precision signal |
| packer/flattener | Dean Edwards p,a,c,k,e,d; obfuscator.io string-array-rotate + _0x hex identifiers; control-flow flattening (switch-dispatch-in-loop density); opaque predicates; dead-code padding | AST shape metrics: dispatch-loop density, hex-identifier ratio, statement/literal ratios, decoder-function fingerprints |
| invisible-text | Unicode bidi overrides (Trojan Source), zero-width characters, homoglyph identifiers | deterministic codepoint scan -- zero false positives, always fatal |
| evasion-triggers | CI/env fingerprint checks guarding payloads, sleep/date delay gates before net/exec | conditional-guard query: env-read or time-read dominating a capability call site |
| stego/side-channel | payloads in test fixtures/images, package.json fields, long comments | entropy scan over non-code files and comment bodies; VET008 divergence corroborates |
| minified-vs-obfuscated | legit npm dist files ARE minified -- the hard false-positive problem | classify against known bundler output shapes (webpack/rollup/terser fingerprints); require dist-to-repo-source correspondence (VET008); minified WITHOUT matching source is treated as obfuscated |

The minified-vs-obfuscated distinction is why the JS path needs VET008
(artifact/source divergence) as a co-detector rather than entropy alone:
minification is normal publishing practice; minification with no
corresponding source is the red flag.

## Declaration and gates (`frob.toml`)

```toml
[vet]
enforce = true
osv = false                    # optional online advisory lookup (osv.dev)

[vet.allow]
requests = ["net", "env"]
pydantic-core = ["native"]
jinja2 = ["eval"]              # sandboxed template compilation, reviewed
```

| Rule | Fails when |
|---|---|
| VET001 | dependency in the lockfile has no `[vet.allow]` entry (absence is an error -- new deps get reviewed before check passes) |
| VET002 | observed capability not in the declaration |
| VET003 | version bump ADDS a capability vs the previously scanned version (fires even if declared -- escalation always warrants a look; re-declare to acknowledge) |
| VET004 | obfuscation signals or install-hook capability beyond declared |
| VET005 | known advisory for a locked version (only when `osv = true`; offline-first default) |
| VET006 | lockfile and manifest disagree (manifest edited without re-lock) |

All waivable per-site is meaningless here (there is no site); VET waivers
live as reviewed `[vet.allow]` edits in a commit -- the declaration IS the
waiver mechanism, and its diff is the audit trail.

## CVE mirror matching (T-0147)

Builds on `frob.cve` (T-0146, parser/models only, no network) with the
matching and CWE-linkage step that module deliberately leaves to `frob
vet`: a local `cvelistV5` mirror clone (`git clone
https://github.com/CVEProject/cvelistV5`) matched against the project's
resolved dependencies, with each hit's `problemTypes[].cweId`s cross-
referenced against the strata threat catalog.

**Configuration** -- the mirror root, not a `[vet]`/`frob.toml` setting
like the rest of this module, since it names a local filesystem path
outside the repo (same reasoning `AppConfig` already applies to every
other path field it reads from `[tool.frob]`):

```toml
# pyproject.toml
[tool.frob]
vet_cve_mirror = "/path/to/cvelistV5"
```

```
frob vet [path] --cve-mirror /path/to/cvelistV5   # CLI flag overrides pyproject.toml
```

**No mirror configured at all** (neither `[tool.frob].vet_cve_mirror` nor
`--cve-mirror`): clean, silent no-op -- `frob vet` runs exactly as it did
before this feature existed. **A mirror path IS configured but missing or
unreadable**: `Err(VetError.CveMirrorInvalid)`, logged at ERROR and
`sys.exit(1)` -- a loud typed failure, never an empty "0 CVEs found"
result (vacuous-pass doctrine: silence must never be confusable between
"nothing wrong" and "could not check").

**Product matching**: a dependency's `name` is matched case-insensitively
against each `affected[].product` string. This is an exact-string join,
not a CPE-dictionary lookup -- real CVE records name products in vendor
prose ("Apache Log4j2") that frequently differs from the package's
registry name ("log4j-core"); a real CPE join is a follow-up, not yet
built (undercounts rather than overclaims, consistent with the rest of
this module's honesty posture).

**Version-range semantics** (`Version.version`/`.lessThan`/
`.lessThanOrEqual`/`.versionType`/`.status`, `Affected.defaultStatus`):
- `lessThan`: half-open range `[version, lessThan)`.
- `lessThanOrEqual`: closed range `[version, lessThanOrEqual]`.
- neither: a single-version point match (`version` of `""`/`"0"` is the
  schema's own "no lower bound" sentinel).
- the LAST matching explicit range in `versions[]` wins (the schema's own
  override-by-order convention); no explicit range matching falls back to
  `defaultStatus`.
- `versionType` gates whether a range is comparable at all: `"semver"`,
  `"python"`, `"pep440"`, and unset (`""`) are compared via
  `packaging.version.Version` (PEP440-ish, semver-ish -- NOT a strict
  semver-spec parser); anything else (git commit hashes, `"custom"`,
  `"rpm"`, ...) -- or a version string that fails to parse even under a
  comparable type -- is `MatchStatus.INDETERMINATE` with a specific
  reason, never silently treated as `UNAFFECTED` (vacuous-pass doctrine:
  Log4Shell's own real record uses `versionType="custom"` with a
  non-semver `lessThan`, and reports INDETERMINATE for exactly this
  reason). `defaultStatus="unknown"` (or absent) with no explicit range
  match is likewise `INDETERMINATE`, not `UNAFFECTED`.
- the nested per-version `changes[]` sub-list (nonlinear affected/
  unaffected flips within a single `versions[]` entry, which Log4Shell's
  own record also carries) is NOT evaluated -- out of scope for this
  slice, disclosed rather than silently approximated; the entry's own
  top-level `version`/`lessThan`/`status` decide the verdict.

**REJECTED records** are skipped with a log line, never matched (a
rejected CVE names no real vulnerability).

**CVSS**: the first `cvssV4_0` metric found across the record's CNA/ADP
containers is preferred; falls back to the first `cvssV3_1` when no v4.0
metric is present. `None`/`None` when the record carries neither.

**CWE linkage**: every matched CVE's `problemTypes[].descriptions[].cweId`
is cross-referenced against `frob.strata._threat.CWE_CATALOG +
CWE_TOP_25_CATALOG` (a hit names the catalog entry's title and
mitigation) and, failing that, `CWE_TOP_25_OUT_OF_SCOPE +
QUALITY_OUT_OF_SCOPE` (a hit names the recorded reason); a CWE id in
neither table is `UNMAPPED` (logged, never dropped).

**Output**: `frob vet --cve-mirror ... [--json]` prints a `cve matches:`
section (CVE id, status, CVSS score/severity, description summary, CWE
linkage) after the normal package table, or a `cve_matches` array folded
into the `--json` payload alongside the existing `VetReport` fields.
Matches are reporting-only in this slice -- no new gate rule feeds them
into `frob check`'s enforce/exit-code path yet (a `VET012`-shaped gate
rule is a natural, still-unbuilt follow-up).

## Mechanics

- **Input**: the lockfiles frob already understands the shape of
  (uv.lock/poetry.lock, Cargo.lock, package-lock.json/pnpm-lock.yaml) --
  name, version, artifact hash per dependency. `scan_tree` scans EVERY
  supported lockfile found directly under the root (`_lockfile.
  _find_all_lockfiles`), not just the first one a fixed-order search
  hits -- as of T-0400, a polyglot repo with both a `uv.lock` and a
  `package-lock.json` gets both ecosystems vetted in one pass; before
  T-0400 the second lockfile's dependencies were silently never scanned.
- **Scan**: fetch/locate the package source (local caches first: uv/pip
  cache, cargo registry cache, node_modules; network fetch only with
  consent), parse with frob.lang, run tree-sitter capability queries
  (shared query files with frob.policy's pattern engine -- one query
  infrastructure, two consumers).
- **Verdict cache**: content-addressed by artifact hash in
  `.frob/vet.db` -- a (package, version, hash) verdict is immutable and
  shared-safe, so full-tree re-vets are incremental and CI-fast. LRU on
  the store like the dup verdict cache.
- **Transitive**: the whole resolved tree is vetted, not just direct deps
  (attacks enter through transitive edges).
- **Progress and bounding (T-0208)**: `_scan_dependencies` logs one INFO
  line per package as it completes (`vet: package M/N name`) so a
  full-lockfile run is observable instead of a silent multi-minute hang.
  `scan_tree(root, *, timeout=..., jobs=...)` takes an optional
  per-package `timeout` in seconds -- on expiry the package gets an
  honest `VET-TIMEOUT` (WARN) verdict with a `"timeout"` signal, never a
  silent drop from the report -- and an optional `jobs` to scan packages
  concurrently in a thread pool. `jobs > 1` is disclosed as best-effort:
  the sqlite verdict cache (`.frob/vet.db`) and the registry publish-date
  disk cache open short-lived per-call connections with no explicit
  cross-thread locking beyond sqlite's own busy handling, so a concurrent
  verdict write can lose a race to another thread's write for the same
  key non-deterministically (never a crash or corruption, just "most
  recent write wins" under contention); `jobs=1` (the default) has none
  of this risk. `frob vet --timeout SECONDS --jobs N` (T-0251) plumbs
  both flags through `AppConfig.vet_timeout`/`vet_jobs`
  (`app/config.py`) and `app/vet_runner.py`'s `_run_scan` into
  `scan_tree` -- unset `--jobs` still defaults to the safe `jobs=1` path,
  so raising it above 1 is an explicit opt-in into the shared-cache race
  disclosed above, not a new default.
- **Advisories (VET005)**: delegated to the osv-scanner adapter (see
  External tool adapters below) -- OSV.dev aggregates GitHub Advisory DB,
  PyPA, RustSec, and npm under one package-keyed schema, and osv-scanner
  already handles batch queries, offline database mirrors, and lockfile
  parsing for ecosystems frob has not met. frob does not hand-roll an
  advisory client alongside it (no duplication). Advisory results cache
  in `.frob/vet.db` with a 24h TTL -- advisories, unlike capability
  verdicts, can appear for an unchanged version, so this is the one vet
  fact expiring by time instead of by hash. Live queries disclose your
  dependency list to a third party, so the default is off; recommended
  posture is off locally, on (or offline-mirror) in CI.
- **Containment (CVE->CWE join, phase D)**: `_containment.py::
  build_containment_report` joins each VET005 advisory's CVE id(s)
  against `frob.strata`'s CWE obligation model via NVD's <!-- frob:waive DOC006 reason="NVD's own external REST API path segment, not a path in this repo" -->`cves/2.0` API,
  cached 7d in the same `.frob/vet.db` (`_nvd.py::fetch_cwe_for_cve`,
  offline-first -- `fetch=False` restricts to cache, degrading loudly to
  `"unverified"` on a miss/failure rather than a silent pass). `state`
  is one of four values, deliberately kept distinct: `"live"`
  (undischarged -- high severity), `"unverified"` (the NVD lookup could
  not be completed -- "we could not check", never conflated with
  no-coverage), `"contained"` (discharged, defense-in-depth), or
  `"unmodeled"` (genuine no-coverage: no covering node, or no catalog
  entry for the mapped CWE). See docs/strata/threat.md "CVE: threat
  intelligence joined to the proof" for the join semantics.
  `render_containment_report` produces the text form, LIVE-then-
  UNVERIFIED-then-CONTAINED-then-UNMODELED ordered so a data-source
  outage is never scrolled past as if it were a routine no-coverage
  result; wiring a <!-- frob:waive DOC006 reason="proposal syntax for a flag not yet added, the same sentence discloses it as a follow-up" -->`frob vet --containment` CLI flag through `app/
  vet_runner.py`/`__main__.py` is a follow-up (out of T-0110's declared
  scope, which is `src/frob/vet/**` only).

## Project-tree-wide supply-chain structural checks (T-1088)

`_supplychain.py::supply_chain_tree_violations` folds four detectors into
`scan_tree`, run once per call (not per dependency, not per lockfile) --
each is a purely structural property of the scanned PROJECT's own tracked
manifests/CI workflows/file tree, not a fetched or resolved dependency
source, mirroring the "statically-detectable" checkability tag
`docs/design/registry/supply-chain.yaml` gives each entry:

- **VET007** (`SC-ATTACK-UNPINNED-DEPENDENCIES`): a `pyproject.toml`/
  `package.json`/`Cargo.toml` dependency spec with no exact pin (a caret,
  tilde, wildcard, or comparison-operator range instead of `==`/`=`).
- **VET008** (`SC-DETECTION-PYTHON-INSTALL-ARTIFACTS`): a `setup.py`/
  `setup.cfg` `data_files` destination that is absolute or escapes the
  package via `../` traversal -- an installed artifact landing somewhere
  unexpected on the target filesystem.
- **VET009** (`SC-DETECTION-UNPINNED-CI-ACTION`): a
  `.github/workflows/*.yaml` `uses: owner/action@ref` where `ref` is a
  mutable branch/tag rather than a full 40-hex-char commit SHA.
- **VET010** (`SC-DETECTION-OPAQUE-BINARY-ARTIFACT`): a tracked binary
  blob (`.whl`/`.so`/`.node`/`.wasm` and similar) with no build recipe
  (`Cargo.toml`/`CMakeLists.txt`/`setup.py`/`Makefile`/etc.) in its own
  directory or any ancestor up to the project root.

`SC-DETECTION-NPM-NON-REGISTRY-SOURCE` needed no new detector -- it was
already covered by the existing `_ecosystem.py::_npm_non_registry_rule`
(VET-JS004), just missing its `frob:enforces` edge and registry
disposition (both T-1088 residue from earlier per-dependency work).

## External tool adapters

frob.vet is a conformance layer, not a rewrite of the scanning ecosystem.
Where a maintained tool already does a job well, vet drives it through a
typed adapter (the lithos toolenv/procio posture: resolve the binary,
honest absence with a teaching message, typed argv, JSON output parsed
into vet's models, never an auto-install):

| Adapter | Tool | Feeds |
|---|---|---|
| advisories | osv-scanner (or pip-audit / cargo-audit as ecosystem fallbacks when osv-scanner is absent) | VET005 |
| malware-heuristics | GuardDog | corroborates VET004 signals with maintained typosquat/exfil rules |
| repo-health | OpenSSF Scorecard | advisory metadata on verdicts (unmaintained, unreviewed-commits) -- informational, not a gate |
| provenance | sigstore/cosign, SLSA attestations | VET007 (new, opt-in): artifact hash lacks valid provenance for packages listed in [vet.require-provenance] |

## First-party detectors (the non-public layer)

Public scanners are the attacker's test suite: malware is iterated until
GuardDog/OSV-adjacent rules pass, so a defense that is only the public
battery is a defense the attacker already ran. vet therefore carries
first-party detectors whose signal derives from baselines an attacker
cannot pre-test against -- your project's declarations, the package's own
history, and the divergence between what different observation methods
see. Obscurity is a bonus here, not the mechanism: these stay strong even
if the method is known, because the baseline is per-target.

| Rule | Detector | Signal |
|---|---|---|
| VET008 | artifact/source divergence | the published sdist/tarball differs from the tagged source repo beyond expected build outputs (the xz shape: the backdoor was in the tarball, not in git) |
| VET009 | stylometric self-similarity | new code in version N+1 is structurally alien to the package's own history -- reuses the frob-core WL-kernel/fingerprint machinery from docs/modules/dup.md pointed at "this package vs itself over time" |
| VET010 | dynamic/static divergence | opt-in detonation: import/install the package in a no-network, syscall-observed sandbox (bwrap/seccomp); capabilities OBSERVED dynamically but invisible statically are the highest-severity finding vet produces (dynamic-import smuggling) |
| signals | cadence + maintainer anomalies | dormant package suddenly releasing, maintainer handover immediately followed by a capability change -- registry metadata feeding VET003/VET004 severity, not standalone rules |

VET010 runs only for new dependencies and escalation events (it is heavy
by design); VET008/VET009 are cheap enough for every version bump. And
`[vet.detectors]` loads project-private tree-sitter query packs and Python
plugin detectors from the repo itself -- rules that exist only in your
tree, which no attacker's CI matrix includes.

Division of labor: adapters supply FINDINGS; frob supplies the
DECLARATION model, the escalation diffs, the verdict cache, and the gate.
frob's own tree-sitter capability scan remains first-party because it is
the differentiator (no maintained tool produces per-package capability
sets across five languages to diff against declarations); everything else
is delegated by default. A missing adapter binary downgrades its rules to
reported-as-skipped (visible in GateStats), never a silent pass -- and
[vet].required_tools = ["osv-scanner"] makes absence itself a violation
for teams that mandate the full battery.
- **Output**: `frob vet` renders a capability manifest table; the gate
  consumes the same verdicts inside `frob check`.

## Honest limits (documented, not hidden)

Static capability analysis cannot see: dynamically constructed imports
resolved at runtime, capabilities inside `native` code, or logic bombs
that misuse an already-declared capability (requests exfiltrating via its
declared `net`). The defense is layered accordingly: `native` requires
explicit trust, obfuscation is unconditionally fatal, escalation diffs
catch the common attack shape, and VET005/osv covers disclosed compromises.
frob.vet raises the cost of the attack classes that actually occur; it is
not a proof of benignity, and the docs say so.

Embedded-code declaration, not full re-parse (T-0244): `embedded_code`
detection is a size + HTML/JS-signal heuristic over python STRING nodes,
not a real HTML/JS parse of the embedded content -- the typescript-needle
re-scan over a region's own text is the same coarse substring philosophy
as every other needle table, so a region can be declared `embedded_code`
while its specific sub-capabilities (`eval`/`html_render`/`fetch_url`/...)
stay unobserved if the embedded content doesn't happen to contain a
matching needle. That is intentional and fail-closed: `embedded_code`
itself is ALWAYS emitted for a detected region regardless of what the
re-scan finds, so the region cannot silently pass unseen (docs/design/
structural-linter-adversarial-hardening.md rule 3) -- it must be declared
or waived in `[vet.allow]` like any other observed capability (VET002).
Detection is python-host-only for this pass (the reported pilot shape);
embedded HTML/JS strings inside TS/rust/C-C++/kotlin hosts are a
documented gap, not attempted here.

Self-match false positives (T-0151): the capability scanner's pattern
tables (`_PATTERNS` in `src/frob/vet/_capability.py`) are plain-text
needles, matched with substring search over raw source text, not an AST.
Any file whose comments, docstrings, or unrelated string literals happen
to contain one of those needles (e.g. a variable-name check for the
literal `"cmdclass"`, or a docstring that mentions `os.environ`) will
report the corresponding capability even though no such call exists.
This is an accepted, DOCUMENTED false-positive class, not silently eaten:
distinguishing "used as a call" from "appears as data" cheaply would
require tokenizing/parsing the scanned file, which the scanner
deliberately does not do (its own header comment: "recall over precision").
Two narrower, cheap mitigations ARE applied: (1) the `eval` capability's
`compile(` needle only fires for a bare builtin call, not a dotted method
access like `re.compile(`/`ast.compile(`, since that dotted form was
responsible for the entire cross-file false-positive set observed before
T-0151 (cli/graphlang/gates/checker/core all spuriously reported "eval"
from ordinary `re.compile(` calls); (2) `scan_directory_capabilities`
excludes `_capability.py`'s own file from directory aggregation, since
its pattern tables are guaranteed to contain every needle as literal
data. Neither mitigation is a general fix: `src/frob/vet/_ecosystem.py`'s
genuine `"cmdclass" in text` install-hook check, for example, still
reports "install-hook" for `vet` itself even though `vet` does not
install-hook anything -- that is the accepted false-positive class this
paragraph documents, exercised by
`TestCapabilityScan::test_capability_module_self_scan_documented_false_positive`
in `tests/test_vet.py`.

High-entropy string scan (T-0208): `high_entropy_strings` finds quoted
literal bodies with a single left-to-right scan (matching quote chars
only, no AST) -- an apostrophe inside a comment or docstring that has no
matching close before the next same-type quote elsewhere in the file will
be read as the boundary, occasionally producing a multi-hundred-char
"literal" spanning several real statements. This is an ACCEPTED,
pre-existing false-positive class inherited from the regex this scan
replaced; the T-0208 change fixed the scan's WORST-CASE TIME (the old
regex's `(?:\\.|(?!\1).)*` alternation backtracks catastrophically over
exactly these long mismatched-quote spans -- 82 of 120 profiled seconds
in one pilot repo, from 785 calls), not its precision.

Two safety valves bound worst-case work per file: a file caps at 4000
candidate literals (`_MAX_CANDIDATES_PER_FILE`), and a single candidate
has a 1MB memory ceiling (`_MAX_CANDIDATE_LEN`) purely to stop an
adversarial multi-hundred-MB "string" from an OOM -- it is not a
normal-path truncation and is never expected to fire on a real source
file. Entropy is ALWAYS computed over the full closed literal, never a
truncated prefix: an earlier version of this fix truncated the content
fed to the entropy check at 4096 chars for perf, which is WRONG, not
just a tradeoff -- Shannon entropy is a property of the whole sample, and
truncating a real hit can pull its score back under threshold. Measured
on a real file (cryptography's `pkcs7.py`, a mismatched-quote span, not
even a genuine payload): `entropy(full 7575-char span) = 4.602` (fires,
matches the old regex), `entropy(same span truncated to 4096) = 4.472`
(silent -- a real detection loss). The scan's O(n) bound does not need a
length cap: every successful (closing) literal's inner scan consumes its
own span exactly once and the outer loop never revisits those
characters, so total scan work across ALL successful literals in a file
is bounded by `len(text)` regardless of how any single literal's length
is distributed -- the only thing that needs to stay O(1) is a FAILED
open, handled by the `last_single`/`last_double` reject described next.
Files over 2MB are skipped for the whole obfuscation scan (DEBUG-logged,
not silent) -- past that size a file reads as a data/vendor blob rather
than something a hand-obfuscated payload hides inside inconspicuously.

One correctness fix and one full-corpus verification, both from review
round 2 (a single-file sample is not evidence; see the T-0208 Done report
for the methodology and full numbers this paragraph summarizes):
1. **Unterminated candidates.** A quote character with no matching close
   anywhere later in the file is NOT a literal (matches the old regex: a
   failed match attempt at that start position, retried one character
   later) -- an earlier version of this fix incorrectly ran such a
   candidate to end-of-file and scored it, which could swallow a
   following real string (e.g. the next docstring) into one bogus
   "literal" and drop it from the entropy check entirely. Fixed via an
   O(1) per-position reject (`last_single`/`last_double`: each quote
   type's last raw occurrence in the file, computed once) so a file with
   many trailing unmatched quote characters stays linear rather than
   reintroducing the T-0208 blowup through the back door.
2. **Full-corpus verification, not a sample.** Old-vs-new compared over
   every `.py` file under this repo's own `.venv/lib/python3.11/
   site-packages` (1475 files) with the old (pathological) implementation
   bounded by a 3s-per-file SIGALRM budget so a handful of genuinely
   intractable files (7 of 1475 -- real files, e.g.
   <!-- frob:waive DOC006 reason="path inside a third-party site-packages install (cryptography), not this repo" -->`cryptography/hazmat/primitives/keywrap.py`,
   <!-- frob:waive DOC006 reason="path inside a third-party site-packages install (pygments), not this repo" -->`pygments/lexers/c_like.py` -- where the OLD regex itself does not
   finish in 3s; this IS the pathology T-0208 exists to fix, not a gap in
   the comparison) don't block comparing the other 1468. Of 1468 compared:
   1 file diverges, and it is the disclosed `_MAX_CANDIDATES_PER_FILE`
   cap (a builtins-list file with exactly 4000+ tiny quoted tokens; the
   4000th candidate cuts off one specific late literal, but two earlier
   ones in the same file already trip the entropy threshold under both
   old and new, so the file's aggregate `high-entropy-string` signal is
   unaffected). Zero files flip from fired-old/silent-new (the one class
   of divergence that would be a real detection loss) after fix #1 and
   the entropy-truncation fix above -- before those two fixes, the same
   corpus check found 14/105 divergent files in `pydantic` alone and 4
   genuine fired-old/silent-new losses corpus-wide.

Prior art is embraced, not reimplemented: GuardDog, pip-audit/osv-scanner,
OpenSSF Scorecard, and sigstore run as adapters (see above). frob's
first-party differentiators: declaration-vs-observation conformance (not
advisory output), version-escalation diffs as the primary signal,
cross-language capability sets via one grammar stack, offline-first, and
gate enforcement.

## Closed-world import accounting (T-0180)

T-0158 shipped the single-source `DANGEROUS_OPERATIONS` registry, the
(kind x language) coverage matrix with 0 unexcused cells, and the
sys-audit matrix-verdict proof line -- but that proof only covers "every
(capability kind, language) cell is patterned or excused." It says nothing
about whether a GIVEN dependency's actual import graph is fully accounted
for. `src/frob/vet/_closedworld.py` closes that separate gap: for one
vetted package, `closed_world_accounting` locates its source, walks every
absolute Python import (`ast.parse`, never a substring guess), and
resolves each import root to exactly one of four buckets, in priority
order:

1. **registry** -- the import matches a `DANGEROUS_OPERATIONS` library for
   the language (via the `library` field, plus a small documented
   PyPI-distribution-name-vs-import-name override table for the two known
   mismatches, `python-dotenv`/`dotenv` and `Pillow`/`PIL`).
2. **no-capability** -- the import is a curated `NO_CAPABILITY_MODULES`
   stdlib entry (T-0158 addendum 2's curated no-effect stdlib set).
3. **vetted** -- the import is either already cached (`_cache.py`'s
   `latest_verdict`) or its source is locatable under the project root, in
   which case it is scanned by the SAME capability engine
   (`scan_directory_capabilities`) and the resulting `PackageVerdict` is
   cached via `_cache.py::store_verdict` -- the identical sqlite pattern
   the primary verdict cache uses, keyed the same way (content-addressed
   artifact hash).
4. **unknown** -- none of the above: not a registry library, not curated
   stdlib, and its source cannot be located locally. This is the LOUD
   failure case -- logged at WARNING, never silently dropped -- and it is
   exactly the honest outcome for e.g. an un-vendored stdlib module this
   repo's `NO_CAPABILITY_MODULES` curation has not reached yet (`uuid`,
   `ipaddress`, `ambiguous` `ast.parse`-only stdlib modules observed during
   manual testing against `pydantic`'s real import graph), or a genuinely
   uninstalled third-party dependency.

`ClosedWorldAccounting.accounting_line()` renders the audit line T-0158's
addendum 2 describes: "N registry op(s), M vetted library/ies, K explicit
no-capability entries, J unknown" for `ecosystem/name@version`.
`ClosedWorldAccounting.closed` is `True` iff the source was actually
available to walk AND `unknown_count == 0` -- an unlocatable source can
never claim closure by omission (`source_available=False` renders as
"source unavailable, closed-world accounting skipped" instead of a
misleadingly-clean zero-everything line).

Honest scope cuts (T-0180, not silently claimed done):
- **Python only.** The import-graph walk is `ast.parse`-based and Python-
  specific. An npm (`import`/`require` AST) or cargo (`use`/`extern
  crate`) import-graph walk is real, tracked, un-built work -- the same
  "curated, not exhaustive" posture `NO_CAPABILITY_MODULES` already
  documents for the Python stdlib subset itself.
- **Single-hop resolution.** `resolve_import` scans a vetted import's OWN
  source for capabilities; it does not recursively walk THAT import's own
  imports (no transitive closure). A vetted dependency with an unresolved
  transitive import of its own is invisible to this pass -- a real gap,
  not a claimed-closed one.
- **`RecursionError` degrades to empty capabilities, not a crash.**
  `_capability_core.py::_comment_byte_spans_from_tree`'s recursive tree-sitter walk hits
  Python's recursion limit on some real, deeply-nested third-party source
  files (observed live against `pydantic`'s installed dependency tree in
  this repo's own `.venv`); `_closedworld.py::_scan_capabilities_best_effort`
  catches it and treats that one dependency as having zero observed
  capabilities (logged at WARNING) rather than aborting the whole
  accounting pass -- the same best-effort posture `_source.py`/`_cache.py`
  already document for their own failure modes.

## Third-party library survey (T-0181)

T-0158 addendum 2's priority survey list of python/npm/cargo third-party
libraries, surveyed against each library's REAL API surface (not guessed)
and dispositioned as either new `DangerousOperation` entries in
`src/frob/vet/_capability_registry/_matrix.py::DANGEROUS_OPERATIONS`, or an
explicit pure-library verdict with no dangerous surface. Every
ticket-listed library appears exactly once below, so none is silently
dropped.

| ecosystem | library | disposition | reasoning |
|---|---|---|---|
| python | pydantic | pure | validation/serialization library; no exec/eval/net/fs primitive of its own |
| python | fastapi | pure | routing/DI framework over Starlette; dangerous surface (raw HTML, static file serving) lives in app-authored handlers or Starlette itself, already covered by the generic entries |
| python | numpy | patterned | `numpy.load(..., allow_pickle=True)` -- deserialize/CWE-502 |
| python | cryptography | pure | crypto primitives; weak-algorithm misuse is not a capability this scanner's taxonomy models |
| python | jinja2 | patterned | `Template()`/`from_string()` SSTI (eval/CWE-1336); `autoescape=False` (html_render/CWE-79) |
| python | python-dotenv | patterned | `load_dotenv(` -- env |
| python | uvicorn | patterned | `uvicorn.run(` -- net (binds/serves a socket) |
| python | sqlalchemy | patterned | `sqlalchemy.text(` with string-formatted SQL -- sql/CWE-89 |
| python | asyncpg | patterned | `asyncpg.connect(` -- net |
| python | alembic | pure | migration execution is by-design running trusted migration code/DDL; no additional API-level pattern distinct from the exec/sql surfaces already covered |
| python | redis | pure (this pass) | connection/command surface is generic net-adjacent; the Lua `EVAL` idiom has no client-name-independent literal substring to pattern without unacceptable false-positive risk -- tracked as a gap, not claimed covered |
| python | boto3 | patterned | `boto3.client(`/`boto3.resource(` -- net (cloud credentials) |
| python | stripe | patterned | `stripe.api_key` -- net (payment API, live secret key) |
| python | anthropic | patterned | `anthropic.Anthropic(` -- net (API key) |
| python | argon2-cffi | pure | password-hashing primitive; a defensive tool, not a dangerous-operation surface |
| python | aiosmtpd | patterned | `aiosmtpd.controller.Controller(` -- net (inbound SMTP server) |
| python | playwright | patterned | `sync_playwright(`/`async_playwright(` browser launch (exec); `page.evaluate(` (eval/CWE-95) |
| python | Pillow | patterned | `ImageMath.eval(` -- eval/CWE-95; decompression-bomb DoS has no matching capability_kind in this registry, tracked as a gap |
| npm | react / react-dom | pure | `dangerouslySetInnerHTML` is already patterned under typescript/html_render; no other dangerous surface |
| npm | vite / vitest | pure | build/test tooling; config files are trusted-author code by design, no additional runtime API pattern |
| npm | playwright | patterned | `chromium.launch(`/`firefox.launch(`/`webkit.launch(` (exec); `page.evaluate(` (eval/CWE-95) |
| npm | openapi-typescript | pure | build-time code generator; no runtime dangerous surface |
| npm | eslint tooling | pure | static-analysis tooling; no runtime dangerous API surface for consumers |
| cargo | pyo3 | patterned | `pyo3::`/`Python::with_gil(` -- ffi (embeds/calls the Python interpreter) |
| cargo | serde / serde_json | pure | type-directed (de)serialization, not string-eval-based (already excused at the matrix-cell level: see `CAPABILITY_MATRIX_EXCUSES` rust/deserialize) |
| cargo | tracing | pure | structured logging/instrumentation; no dangerous surface |
| cargo | libloading | already covered | patterned under rust/ffi since T-0158 (`libloading::`) |
| cargo | wasm-bindgen | patterned | `wasm_bindgen::`/`#[wasm_bindgen]` -- ffi (Rust/JS wasm boundary) |
| cargo | crossbeam | pure | concurrency primitives; no dangerous surface |
| cargo | thiserror | pure | error-derive macro; no dangerous surface |

### T-0222: socket/uvicorn "bind" observability (investigation, no new kind)

Sibling-pilot P1 gap 5 asked for a `bind`/`listen` capability needle so a
server that binds a port is observable. Investigation found this already
patterned, not missing: `uvicorn.run(` (row above) and the c-cpp
`socket()/connect()/bind()` entry both already fire `net` -- the tier-2
`may` vocabulary (`frob.strata._effects._KIND_MAP`) delegates only
`net`/`fs`/`exec`, so a distinct `bind` kind would duplicate `net` rather
than add a new discharge shape (the exact anti-pattern
[Benign capabilities](../guides/extending/benign-capabilities.md#common-
mistakes) warns against -- "confusing this vocabulary with the threat
catalog's"). No new kind added. The one real gap this pass closes is
narrower: Python's low-level `from socket import socket` import idiom
(no `socket.` substring) is still scanner-invisible under the existing
`socket.socket/create_connection` needle -- left as a known, documented
gap (not claimed fixed) since a bare `.bind(`/`.listen(` needle would
collide with unrelated APIs (`tkinter.Widget.bind`, SQLAlchemy's
`Engine.bind`) with no cheap discriminator, the same false-positive-risk
discipline `_capability.py`'s module docstring already documents for
`compile(`/`napi`.

## Public API

T-0972: `non_executable_line_numbers` (`src/frob/vet/_capability.py`)
picked up a reasoned `frob:waive PERF002` on its own per-span
`raw.count(b"\n", ...)` call (each `(start, end)` span needs its own
byte-count query over a different sub-range; not a repeated identical
count to hoist) -- no behavior change.

T-1067: `_nvd.py`'s and `_registry.py`'s previously near-identical private
`_cache_get`/`_cache_set` sqlite TTL-cache helpers (differing only in
table name and TTL) were extracted into one shared, table/TTL-parametrized
home, `_cache.py::ttl_cache_get`/`ttl_cache_set`; both callers now pass
their own table name and TTL in rather than re-deriving the open/query/
expiry-check/return-or-None shape. No behavior change (`_nvd.py` still
uses table `nvd_cache` and a 7d TTL; `_registry.py` still uses table
`cache` and a 24h TTL).

<!-- frob:describes src/frob/vet/_models.py::Dependency -->
<!-- frob:describes src/frob/vet/_models.py::PackageVerdict -->
<!-- frob:describes src/frob/vet/_models.py::VetReport -->
<!-- frob:describes src/frob/vet/_models.py::capability_diff -->
<!-- frob:describes src/frob/vet/_models.py::HookVerdict -->
<!-- frob:describes src/frob/vet/_models.py::VetConfig -->
<!-- frob:describes src/frob/vet/_models.py::_HookAction -->
<!-- frob:describes src/frob/vet/_models.py::VetError -->
<!-- frob:describes src/frob/vet/_ecosystem.py::_python_rules -->
<!-- frob:describes src/frob/vet/_ecosystem.py::_rust_rules -->
<!-- frob:describes src/frob/vet/_ecosystem.py::_npm_non_registry_rule -->
<!-- frob:describes src/frob/vet/_cache.py::_store_verdict -->
<!-- frob:describes src/frob/vet/_cache.py::_latest_verdict -->
<!-- frob:describes src/frob/vet/_cache.py::ttl_cache_get -->
<!-- frob:describes src/frob/vet/_cache.py::ttl_cache_set -->
<!-- frob:describes src/frob/vet/_hook.py::parse_hook_command -->
<!-- frob:describes src/frob/vet/_hook.py::check_package -->
<!-- frob:describes src/frob/vet/_lockfile.py::_find_lockfile -->
<!-- frob:describes src/frob/vet/_lockfile.py::_find_all_lockfiles -->
<!-- frob:describes src/frob/vet/_lockfile.py::_parse_lockfile -->
<!-- frob:describes src/frob/vet/_capability.py::language_for -->
<!-- frob:describes src/frob/vet/_capability.py::scan_file_capabilities -->
<!-- frob:describes src/frob/vet/_capability_scan.py::_scan_file_fingerprints -->
<!-- frob:describes src/frob/vet/_capability_scan.py::_decode_to_exec_signal -->
<!-- frob:describes src/frob/vet/_capability_scan.py::_scan_directory_capabilities -->
<!-- frob:describes src/frob/vet/_capability_scan.py::_scan_directory_fingerprints -->
<!-- frob:describes src/frob/vet/_capability.py::non_executable_line_numbers -->
<!-- frob:describes src/frob/vet/_scan.py::scan_tree -->
<!-- frob:describes src/frob/vet/_lifecycle.py::_scan_lifecycle_scripts -->
<!-- frob:describes src/frob/vet/_obfuscation.py::_high_entropy_strings -->
<!-- frob:describes src/frob/vet/_obfuscation.py::_invisible_text_signal -->
<!-- frob:describes src/frob/vet/_obfuscation.py::_hex_identifier_ratio_signal -->
<!-- frob:describes src/frob/vet/_obfuscation.py::_scan_text_obfuscation -->
<!-- frob:describes src/frob/vet/_obfuscation.py::_scan_directory_obfuscation -->
<!-- frob:describes src/frob/vet/_popular_pypi.py::PYPI_TOP -->
<!-- frob:describes src/frob/vet/_popular_cargo.py::CARGO_TOP -->
<!-- frob:describes src/frob/vet/_popular_npm.py::NPM_TOP -->
<!-- frob:describes src/frob/vet/_popular.py::ECOSYSTEM_POPULAR -->
<!-- frob:describes src/frob/vet/_registry.py::LATEST_VERSION -->
<!-- frob:describes src/frob/vet/_allow.py::_load_vet_config -->
<!-- frob:describes src/frob/vet/_typosquat.py::_damerau_levenshtein -->
<!-- frob:describes src/frob/vet/_typosquat.py::_find_typosquat -->
<!-- frob:describes src/frob/vet/_osv.py::OsvAdvisory -->
<!-- frob:describes src/frob/vet/_osv.py::_is_available -->
<!-- frob:describes src/frob/vet/_osv.py::_run_osv_scan -->
<!-- frob:describes src/frob/vet/_registry.py::_RegistryResult -->
<!-- frob:describes src/frob/vet/_registry.py::_fetch_publish_date -->
<!-- frob:describes src/frob/vet/_source.py::_locate_pypi_source -->
<!-- frob:describes src/frob/vet/_source.py::_locate_npm_source -->
<!-- frob:describes src/frob/vet/_source.py::_locate_cargo_source -->
<!-- frob:describes src/frob/vet/_source.py::_locate_source -->
<!-- frob:describes src/frob/vet/_osv.py::cve_ids -->
<!-- frob:describes src/frob/vet/_nvd.py::NvdResult -->
<!-- frob:describes src/frob/vet/_nvd.py::fetch_cwe_for_cve -->
<!-- frob:describes src/frob/vet/_containment.py::ContainmentFinding -->
<!-- frob:describes src/frob/vet/_containment.py::ContainmentReport -->
<!-- frob:describes src/frob/vet/_containment.py::find_importing_nodes -->
<!-- frob:describes src/frob/vet/_containment.py::build_containment_report -->
<!-- frob:describes src/frob/vet/_containment.py::render_containment_report -->
<!-- frob:describes src/frob/vet/_containment.py::LIVE -->
<!-- frob:describes src/frob/vet/_containment.py::UNVERIFIED -->
<!-- frob:describes src/frob/vet/_containment.py::CONTAINED -->
<!-- frob:describes src/frob/vet/_containment.py::UNMODELED -->
<!-- frob:describes src/frob/vet/_cve.py::MatchStatus -->
<!-- frob:describes src/frob/vet/_cve.py::CweDisposition -->
<!-- frob:describes src/frob/vet/_cve.py::CweLink -->
<!-- frob:describes src/frob/vet/_cve.py::CveMatch -->
<!-- frob:describes src/frob/vet/_cve.py::link_cwe_ids -->
<!-- frob:describes src/frob/vet/_cve.py::match_dependencies_against_mirror -->
<!-- frob:describes src/frob/vet/_models.py::ImportResolution -->
<!-- frob:describes src/frob/vet/_models.py::ClosedWorldAccounting -->
<!-- frob:describes src/frob/vet/_closedworld.py::walk_python_imports -->
<!-- frob:describes src/frob/vet/_closedworld.py::resolve_import -->
<!-- frob:describes src/frob/vet/_closedworld.py::closed_world_accounting -->

- `Dependency` -- one resolved (ecosystem, name, version[, resolved-URL])
  tuple read from a lockfile; the unit every rule operates on.
- `PackageVerdict` -- one package's scan outcome: observed capabilities,
  signals, and the artifact hash the verdict cache keys on.
- `VetReport` -- the merged `frob vet` result: all verdicts plus all
  violations for one lockfile pass.
- `capability_diff` -- capabilities `cur` has that `prev` did not; the
  VET003 escalation signal, pure and order-stable.
- `HookVerdict` -- one package's pre-install (`--hook`) disposition, since
  it is not yet in a lockfile to scan normally.
- `VetConfig` -- the loaded `[vet]`/`[vet.allow]` table from frob.toml,
  `present=False` meaning advisory-only (no frob.toml section).
- `HookAction` -- a parsed hook command's install-vs-ignore disposition.
- `VetError` -- the fallible outcomes `Result`-typed vet operations return.
- `python_rules` -- VET-PY001/002/003 local file-shape checks (setup.py
  cmdclass, `.pth` files, pickle payloads) for one Python dependency.
- `rust_rules` -- VET-RS001/002 checks (build.rs capability scan,
  proc-macro presence) for one Rust dependency.
- `npm_non_registry_rule` -- VET-JS004: flags a dependency resolved to a
  non-registry (git/http/file) source.
- `store_verdict` -- best-effort persist of a verdict into `.frob/vet.db`,
  content-addressed by artifact hash.
- `latest_verdict` -- the most recently stored verdict for a package name,
  used as the VET003 escalation baseline.
- `parse_hook_command` -- tokenizes a shell command string into
  `(ecosystem, ((name, version), ...))` for recognized install forms.
- `check_package` -- quarantine + typosquat check for one not-yet-installed
  package named in a `--hook` command.
- `find_lockfile` -- the first supported lockfile found directly under a
  project root.
- `parse_lockfile` -- dispatches a lockfile path to its format-specific
  parser, returning the resolved `Dependency` tuples.
- `language_for` -- maps a source file's extension to its capability
  pattern-table bucket (or `None` for unsupported languages).
- `scan_file_capabilities` -- capability tokens observed in one source
  file's raw text, via the per-language substring table, plus (for python,
  typescript, rust, C/C++, and kotlin) import/alias-aware binding
  resolution that catches evasions the raw-text needle scan alone misses
  (T-0328/T-0377/T-0378/T-0379/T-0662/T-0663/T-0664).
- `non_executable_line_numbers` -- T-0769: 1-indexed line numbers in a
  file that a comment or python docstring span touches -- the shared
  primitive `frob.strata._effects`'s line-level THREAT004 observation
  scan uses to get the same comment/docstring exclusion this module's own
  raw-text scanners apply, instead of a needle-in-line check with no
  prose awareness at all.
- `RUNTIME_OPAQUE_CONSTRUCTS` -- T-0665: every coordinator-signed
  category-1 "evasion-indicative dynamic lookup" construct
  (`eval`/`exec`, non-literal `getattr`/`setattr`/`__import__`/
  `importlib.import_module`, non-literal `dlsym`, non-literal JS/TS
  dynamic `import()`, reflection APIs, `libloading` symbol lookup) that
  `frob.gates._opaque.opaque_gate`'s `OPAQUE001` fires on when found with
  no `frob:waive` -- the fail-closed sibling of `DANGEROUS_OPERATIONS`'s
  ordinary resolver-visible table.
- `OPAQUE_SOURCE_INVISIBLE` -- T-0665: REG011-compliant "none --
  &lt;explanation&gt;" dispositions for the taxonomy's runtime-opaque rows
  no per-file source scan can ever see (linker weak-symbol
  interposition, runtime vtable patching) -- excused, not silently
  dropped, cross-registered in `docs/design/registry/check-coverage.yaml`.
- `scan_file_fingerprints` -- T-0153: `frob.strata.CVE_FINGERPRINTS` entries
  whose needle(s) matched in one source file's raw text (the CVE-fingerprint
  sibling of `scan_file_operations`, docs/strata/threat.md#cve-fingerprints-
  code-level-pattern-catalog-t-0153), UNIONED (T-0380) with every
  fingerprint reached via the same python/typescript/rust/c-cpp binding
  tables capability resolution already built (T-0328/T-0377/T-0378/
  T-0379) -- an aliased import that evades the lexical needle scan (`import
  pickle as p; p.loads(...)` never contains the literal text
  `"pickle.loads("`) is still caught through the resolved call/attribute
  target.
- `_binding_fingerprints` -- T-0380: the resolver-backed half of
  `scan_file_fingerprints`, mirroring `_python_binding_operations`'s shape
  exactly against `CVE_FINGERPRINTS` instead of `DANGEROUS_OPERATIONS`.
- `decode_to_exec_signal` -- true when a decode-ish and an exec-ish token
  co-occur in the SAME function body (the highest-precision obfuscation
  signal).
- `scan_directory_capabilities` -- aggregates capability tokens and the
  decode-to-exec signal across every scannable file under a source tree.
- `scan_directory_fingerprints` -- T-0153: aggregates `scan_file_
  fingerprints` matches across every scannable file under a source tree;
  called from `_scan.py::_scan_source` (VET006), the same call site
  `scan_directory_capabilities` already runs from.
- `scan_tree` -- the full-lockfile `frob vet` pass: allow conformance,
  quarantine, typosquat, capability/obfuscation scan, and the osv adapter.
- `scan_lifecycle_scripts` -- packages under `node_modules` declaring
  preinstall/install/postinstall/prepare scripts (VET-JS lifecycle).
- `high_entropy_strings` -- string literals whose Shannon entropy exceeds
  the baseline, i.e. likely base64/hex/packed payloads.
- `invisible_text_signal` -- true if the text contains a Unicode bidi
  override, zero-width character, or non-leading BOM (Trojan Source).
- `hex_identifier_ratio_signal` -- true when `_0x...`-style identifiers
  dominate the identifier population (obfuscator.io's default rename).
- `scan_text_obfuscation` -- all obfuscation signal names present in one
  text blob (empty tuple means clean).
- `scan_directory_obfuscation` -- union of obfuscation signals across every
  text-ish file under a source tree.
- `PYPI_TOP` -- bundled top-PyPI package names, the VET-JS003-generalized
  typosquat-distance baseline for the PyPI ecosystem.
- `CARGO_TOP` -- bundled top-crates.io package names, same role for Rust.
- `NPM_TOP` -- bundled top-npm package names, same role for JS/TS.
- `ECOSYSTEM_POPULAR` -- `PYPI_TOP`/`NPM_TOP`/`CARGO_TOP` indexed by
  ecosystem name, the lookup `find_typosquat` dispatches through.
- `LATEST_VERSION` -- the sentinel version string meaning "resolve
  whatever is newest" rather than a pinned version.
- `load_vet_config` -- reads `frob.toml`'s `[vet]`/`[vet.allow]` tables;
  a missing table means advisory-only mode.
- `damerau_levenshtein` -- OSA edit distance (insert/delete/substitute/
  transpose) between two names.
- `find_typosquat` -- the popular-package name a given name is a likely
  typosquat of, or `None`.
- `OsvAdvisory` -- one osv-scanner advisory finding (id, package, version,
  fixed version if known).
- `is_available` -- whether the `osv-scanner` binary is resolvable on PATH.
- `run_osv_scan` -- advisories for a lockfile via osv-scanner, or `None`
  when the adapter is absent/failed (never treated as "no findings").
- `RegistryResult` -- outcome of a publish-date lookup; `ok=False` means
  "could not verify" (never a hard failure offline).
- `fetch_publish_date` -- the publish timestamp for `name@version` from
  the ecosystem registry, cached 24h.
- `locate_pypi_source` -- a local directory containing a Python
  dependency's source, checked across venv and uv/pip caches.
- `locate_npm_source` -- a local directory containing a JS/TS dependency's
  source under `node_modules/`.
- `locate_cargo_source` -- a local directory containing a Rust
  dependency's source under `~/.cargo/registry/src`.
- `cve_ids` -- the CVE-shaped ids naming an `OsvAdvisory` (its own id plus
  any `aliases`); empty when the advisory has no CVE alias (GHSA/PYSEC/
  RUSTSEC-only), honestly excluded from the containment join rather than
  guessed at.
- `NvdResult` -- outcome of an NVD CVE->CWE lookup; `ok=False` means
  "could not verify" (never "no weaknesses" -- same posture as
  `RegistryResult`).
- `fetch_cwe_for_cve` -- the CWE ids NVD lists for one CVE, cached 7d in
  `.frob/vet.db`; `fetch=False` restricts to the existing cache and
  degrades to `ok=False` on a miss rather than calling out.
- `ContainmentFinding` -- one CVE joined against the strata obligation
  model: its CWE ids, the covering node (if any), and a `state` of
  `"live"` (undischarged obligation -- high severity), `"unverified"`
  (the NVD lookup itself failed -- "we could not check", distinct from
  and sorted ahead of no-coverage so a data-source outage is never read
  as benign), `"contained"` (discharged, defense-in-depth), or
  `"unmodeled"` (no covering node or no catalog entry -- genuine
  no-coverage, never conflated with either "contained" or "unverified").
- `ContainmentReport` -- every `ContainmentFinding` from one
  `build_containment_report` pass.
- `find_importing_nodes` -- node ids whose `code=`-bound files import a
  given dependency's likely top-level module name.
- `build_containment_report` -- joins osv-scanner advisories against a
  `frob.strata` `KernelModel`'s CWE obligations via NVD CVE->CWE data
  (docs/strata/threat.md "CVE: threat intelligence joined to the proof").
- `render_containment_report` -- human-readable text rendering of a
  `ContainmentReport`, ordered LIVE, then UNVERIFIED, then CONTAINED,
  then UNMODELED.
- `locate_source` -- dispatches to the ecosystem-appropriate local-cache
  source locator.
- `ImportResolution` -- one imported module name's closed-world
  classification (T-0180): `"registry"`, `"no-capability"`, `"vetted"`, or
  the loud `"unknown"` fallthrough.
- `ClosedWorldAccounting` -- the full closed-world import accounting for
  one vetted package (T-0180): every import resolved, the four-bucket
  counts, and `closed` (true iff source was available AND zero unknowns).
- `walk_python_imports` -- every top-level module name a package's Python
  source absolutely imports, via `ast.parse` (relative imports excluded).
- `resolve_import` -- classifies one imported module name against the
  `DANGEROUS_OPERATIONS` registry, `NO_CAPABILITY_MODULES`, a
  scan-and-cache vetted-library lookup, or unknown, in that priority order.
- `closed_world_accounting` -- locates a package's source, walks its
  imports, and resolves each one; the T-0158 addendum 2 audit line.

```python
# frob/vet/_models.py
class Dependency(BaseModel):       # frozen
    ecosystem: str
    name: str
    version: str
    resolved: str = ""             # non-registry URL, when the lockfile records one

class PackageVerdict(BaseModel):   # frozen; content-addressed by hash
    name: str
    version: str
    ecosystem: str
    artifact_hash: str = ""
    capabilities: frozenset[str] = frozenset()
    signals: tuple[str, ...] = ()

class VetReport(BaseModel):        # frozen
    verdicts: tuple[PackageVerdict, ...] = ()
    violations: tuple[Violation, ...] = ()   # VET001..VET006, gate-shaped
    enforce: bool = False
    advisory_only: bool = False
    skipped: tuple[str, ...] = ()

def capability_diff(prev: PackageVerdict, cur: PackageVerdict) -> tuple[str, ...]

class HookVerdict(BaseModel):      # frozen
    package: str
    ecosystem: str
    verdict: str
    message: str
    blocked: bool

class VetConfig(BaseModel):        # frozen
    present: bool = False
    enforce: bool = False
    osv: bool = False
    quarantine_days: int = 14
    registry_base_url: str | None = None
    allow: Mapping[str, tuple[str, ...] | bool] = {}

class HookAction(StrEnum):
    INSTALL = "install"
    IGNORE = "ignore"

class VetError(ErrorSet):
    LockfileUnsupported = "No parser for this lockfile format"
    SourceUnavailable   = "Package source not in local caches; rerun with --fetch"
    CacheCorrupt        = "vet cache unreadable; delete .frob/vet.db to rebuild"
    ConfigMalformed     = "frob.toml [vet]/[vet.allow] table is malformed"
    CveMirrorInvalid    = "CVE mirror path is configured but missing or unreadable"

# frob/vet/_ecosystem.py
def python_rules(dep: Dependency, source_dir: Path, lockfile_name: str) -> list[Violation]
def rust_rules(dep: Dependency, source_dir: Path, lockfile_name: str) -> list[Violation]
def npm_non_registry_rule(dep: Dependency, lockfile_name: str) -> Violation | None

# frob/vet/_cache.py
def store_verdict(db_path: Path, verdict: PackageVerdict) -> None
def latest_verdict(db_path: Path, ecosystem: str, name: str) -> PackageVerdict | None

# frob/vet/_hook.py
def parse_hook_command(command: str) -> tuple[str, tuple[tuple[str, str], ...]] | None
def check_package(ecosystem: str, name: str, version: str, *, root: Path) -> HookVerdict

# frob/vet/_lockfile.py
def find_lockfile(root: Path) -> Path | None
def parse_lockfile(path: Path) -> Result[tuple[Dependency, ...], VetError]

# frob/vet/_capability.py
def language_for(path: Path) -> str | None
def scan_file_capabilities(path: Path) -> frozenset[str]
def decode_to_exec_signal(path: Path) -> bool
def scan_directory_capabilities(source_dir: Path, *, max_files: int = 500) -> tuple[frozenset[str], bool]

# frob/vet/_scan.py
def scan_tree(root: Path, *, fetch: bool = True, timeout: float | None = None, jobs: int = 1) -> Result[VetReport, VetError]

# frob/vet/_supplychain.py (T-1088)
def supply_chain_tree_violations(project_root: Path) -> list[Violation]

# frob/vet/_lifecycle.py
def scan_lifecycle_scripts(root: Path) -> dict[str, tuple[str, ...]]

# frob/vet/_obfuscation.py
def high_entropy_strings(text: str) -> tuple[str, ...]
def invisible_text_signal(text: str) -> bool
def hex_identifier_ratio_signal(text: str) -> bool
def scan_text_obfuscation(text: str) -> tuple[str, ...]
def scan_directory_obfuscation(source_dir: Path, *, max_files: int = 500) -> tuple[str, ...]

# frob/vet/_allow.py
def load_vet_config(root: Path) -> VetConfig

# frob/vet/_typosquat.py
def damerau_levenshtein(a: str, b: str) -> int
def find_typosquat(ecosystem: str, name: str) -> str | None

# frob/vet/_osv.py
class OsvAdvisory:
    advisory_id: str
    package: str
    version: str
    fixed_version: str | None

def is_available() -> bool
def run_osv_scan(lockfile: Path) -> tuple[OsvAdvisory, ...] | None

# frob/vet/_registry.py
class RegistryResult(BaseModel):   # frozen
    ok: bool
    published_at: datetime | None = None
    resolved_version: str | None = None
    note: str = ""

def fetch_publish_date(
    ecosystem: str, name: str, version: str, *,
    cache_path: Path, base_url: str | None = None, timeout_s: float = 5.0,
) -> RegistryResult

# frob/vet/_source.py
def locate_pypi_source(root: Path, name: str, version: str) -> Path | None
def locate_npm_source(root: Path, name: str) -> Path | None
def locate_cargo_source(name: str, version: str) -> Path | None
def locate_source(root: Path, ecosystem: str, name: str, version: str) -> Path | None

# frob/vet/_closedworld.py (T-0180)
def walk_python_imports(source_dir: Path, *, max_files: int = 300) -> frozenset[str]
def resolve_import(
    import_name: str, *, root: Path, cache_path: Path,
    language: str = "python", ecosystem: str = "pypi",
) -> ImportResolution
def closed_world_accounting(
    root: Path, ecosystem: str, name: str, version: str, *, cache_path: Path,
) -> ClosedWorldAccounting
```

## Sequencing and integration

- Phase 9 (0.2.x), after frob-core lands (capability queries are cheap,
  but sdist walking wants the incremental cache infrastructure matured).
- CLI: `frob vet [--fetch] [--json]`; gate stage in `frob check` when
  `[vet].enforce = true`.
- Supersedes the earlier "POL kind=dependency" idea: license and pinning
  checks fold into frob.vet as VET-family rules rather than a parallel
  policy kind.

## Implementation notes (T-0008, capability-scan slice)

What landed on top of the lockfile-conformance MVP:

- **Capability scan** (`_capability.py`): per-language substring scan over
  `frob.lang`-parsed source, dispatched by extension. Python, TypeScript/JS,
  and Rust each get a pattern table for exec/eval/net/fs-write/fs-read/
  env/ffi/install-hook. C/C++ intentionally return an empty capability set (no
  idiomatic literal exists yet) rather than a false claim of coverage.
  `decode_to_exec_signal` uses `frob.lang` symbol extraction so a decode
  call and an exec/eval call must land in the SAME function body to count
  -- the highest-precision obfuscation signal, per the docs above.
  T-0170 adds a `kotlin` column (`.kt`/`.kts`) for Android nodes: net
  (OkHttp/`okhttp3.`, `Retrofit.Builder(`, `HttpURLConnection`), exec
  (`Runtime.getRuntime().exec(`, `ProcessBuilder(`), and client_storage
  (`SharedPreferences`/`getSharedPreferences(`, `RoomDatabase`/
  `@Database(`). `eval` is deliberately left unpatterned -- Kotlin has no
  idiomatic string-eval/dynamic-code-execution primitive in common Android
  use, the same "excuse honestly" posture the registry's rust/eval-
  adjacent `MatrixExcuse` entries record. Unlike every other language
  column, `kotlin`'s needle table (`_KOTLIN_PATTERNS`) is hand-maintained
  directly in `_capability.py` rather than compiled from
  `_capability_registry.DANGEROUS_OPERATIONS`: T-0170's declared scope
  covers `_capability.py`/tests/this doc only, not
  `src/frob/vet/_capability_registry/` (a single file until T-1420 split it
  into a package), so `kotlin` could not be added
  to the registry's `LANGUAGES` tuple or given a formal `MatrixExcuse` for
  its unpatterned cells (eval, fs/fs-write/fs-read, ffi, install-hook,
  html_render, sql, fetch_url, deserialize) in the same change, and
  `scan_file_operations` (the named-entry-citing sibling of
  `scan_file_capabilities`) returns no entries for kotlin files as a
  result -- only the bare-kind `scan_file_capabilities` path works for
  kotlin today. `SCANNED_LANGUAGES` and `_capability_registry.LANGUAGES`
  are consequently allowed to diverge by exactly `{"kotlin"}`
  (`UNREGISTERED_SCANNED_LANGUAGES`, T-0170); the T-0169 drift-lock test
  (`tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock`)
  subtracts that set before comparing, so the check stays fully strict for
  every other language. A follow-up ticket to migrate `kotlin` into the
  registry (full T-0158 matrix discipline) was filed rather than expanding
  this ticket's scope; see T-0170's Done report for the id.
- **Source location** (`_source.py`): best-effort local-cache lookup only
  (`.venv/lib/*/site-packages`, `~/.cache/uv`, `~/.cache/pip`,
  `node_modules/<name>`, `~/.cargo/registry/src`). No network fetch is
  implemented; a dependency not found locally scans with an empty
  capability set plus a `source-unavailable` signal AND, as of T-0400, a
  fail-CLOSED `VET-SOURCE-UNAVAILABLE` ERROR violation (`_scan.py::
  _source_unavailable_violation`) -- never a crash, and never a silent
  "clean" verdict indistinguishable from a package that was actually
  scanned and found benign. Before T-0400 this case emitted the signal
  but zero violations, so an allow-listed dependency whose code was never
  installed locally silently "passed" vet without ever being read.
- **Obfuscation ensemble** (`_obfuscation.py`, VET004): string-literal
  Shannon entropy vs a fixed per-language threshold, Unicode bidi/zero-
  width/BOM scan (deterministic, always fatal), and hex-identifier ratio
  (`_0x...` obfuscator.io fingerprint). All three plus decode-to-exec are
  fatal (VET004 ERROR) the instant they fire -- no "deobfuscate and judge."
  CUT from this slice: packer/flattener AST-shape metrics (dispatch-loop
  density, opaque predicates), evasion-trigger conditional-guard queries,
  stego scans over non-code files, and the VET008 divergence co-detector
  that would let minified-vs-obfuscated be told apart reliably. Documented
  here rather than half-implemented against data this scan doesn't have.
- **Verdict cache** (`_cache.py`): sqlite `.frob/vet.db`, content-addressed
  by `(ecosystem, name, artifact_hash)`, plus a "most recent by name"
  lookup that VET003 uses as the escalation baseline. `capability_diff`
  (public API, `frob/vet/_models.py`) is the pure diff function; `_scan.py`
  wires it to VET003.
- **Conformance upgrade**: `[vet.allow]` entries that are a list are now
  read as capability tokens (`requests = ["net", "env"]`); an observed
  capability outside that list is VET002. A bare `name = true` still means
  "any capability" (unchanged MVP behavior) so existing declarations do not
  need to be rewritten immediately.
- **Per-ecosystem cheap rules** (`_ecosystem.py`): VET-PY001 (setup.py with
  `cmdclass`), VET-PY002 (`.pth` files), VET-PY003 (pickle/marshal payloads
  in package data, WARN severity), VET-RS001 (build.rs capability-scanned
  like any package file), VET-RS002 (proc-macro crate presence), VET-JS004
  (non-registry `resolved` URLs in package-lock.json, WARN). CUT: VET-PY001's
  "when a wheel exists" qualifier and VET-PY004 (index-priority confusion)
  need registry/index metadata this local-cache scan doesn't have;
  VET-JS002 (dependency confusion against `[vet].internal_scopes`) needs a
  config field and registry-vs-scope resolution logic not yet added;
  VET-RS003 ([patch]/git substitutions) needs `Cargo.lock` `source` field
  parsing the MVP lockfile parser doesn't capture; VET-C family needs a
  CMake/conan/vcpkg lockfile parser frob doesn't have yet. All are next-
  ticket candidates, not silently dropped.
- **Models**: `PackageVerdict.capabilities`/`.signals` were already present
  in the MVP models (frozen, from the start) and are now actually populated;
  `Dependency.resolved` (default `""`) was added to carry npm's `resolved`
  URL for VET-JS004. No new `VetError` members were needed -- the existing
  `SourceUnavailable` member already covers the "no local source" case,
  surfaced as a per-package `source-unavailable` signal rather than a
  scan-wide error (a single dependency's missing source should not fail
  the whole tree).
- **`vet_runner.py`**: untouched, per instructions. `PackageVerdict.
  capabilities`/`.signals` already flowed through `report.model_dump_json()`
  and the table printer's per-package notes column, so the new fields
  surface automatically with no runner changes.

## Implementation notes (T-0147, CVE mirror matching)

- **New module** `_cve.py`: `match_dependencies_against_mirror` walks a
  mirror with `frob.cve.iter_mirror`, matches each dependency by
  case-insensitive product name, evaluates version-range membership
  (`_status_for_affected`/`_evaluate_entry`, `packaging.version` for
  PEP440/semver-ish comparison), and links CWE ids into the strata threat
  catalog (`link_cwe_ids`). See "CVE mirror matching" above for the full
  semantics.
- **Circular import**: `frob.strata` imports `frob.vet._capability`
  (capability scanning feeds strata's effects model), so `_cve.py`
  importing `frob.strata._threat` at module load time would deadlock the
  import graph. `_cwe_catalog_index`/`_cwe_out_of_scope_index` import it
  lazily (call time) instead -- the only place this module reaches outside
  `frob.vet`/`frob.cve`.
- **Config**: `AppConfig.vet_cve_mirror` (new field, `src/frob/app/
  config.py`) plus `--cve-mirror` on the `vet` subparser (`src/frob/
  __main__.py`) and the `_cve_matches_for` dispatch in `vet_runner.py` --
  touched despite being outside this ticket's declared `src/frob/vet/**`/
  `src/frob/cve/**` scope because the ticket's own "explicit CLI flag
  override" requirement is unsatisfiable without CLI wiring; the scope
  extension is recorded in T-0147's Done report.
- **New `VetError` member**: `CveMirrorInvalid`, the loud typed failure for
  a configured-but-missing/unreadable mirror.
- **Gate integration**: NOT built in this slice -- `frob vet --cve-mirror`
  reports matches (table/JSON) but does not add a new `VET`-numbered rule
  to `VetReport.violations`, so a `frob check` run does not yet fail on a
  live dependency CVE. A `VET012`-shaped rule (ERROR on `AFFECTED`, WARN
  on `INDETERMINATE`) is the natural follow-up; the ticket's own text asks
  for "report", not "gate", so this is a disclosed cut rather than a
  silent one.
- **Product matching**: exact case-insensitive string match against
  `affected[].product`, not a CPE-dictionary join -- see "CVE mirror
  matching" above for why (undercounts, never overclaims).
- **Fixtures**: `tests/unit/cve/fixtures/vet_mirror/` is a second, small,
  synthetic mirror (two records: one PUBLISHED with clean semver ranges,
  one REJECTED) alongside the T-0146 real-record mirror -- none of the
  T-0146 fixtures happen to carry a clean, comparable semver range (curl's
  real record has two never-satisfiable ranges; Log4Shell's is
  `versionType=custom`), and `tests/unit/cve/test_parser.py` asserts an
  exact file count over the T-0146 mirror directory, so adding files there
  would have broken it.

## SEC005 taint rule (T-0781)

`frob.vet._taint.taint_findings` is the intra-function/intra-module taint
pass behind the SEC005 gate (`frob.gates._taint_gate`): a value parsed
from repo-writable state (`.git/`- or `.frob/`-relative reads) reaching a
`subprocess`/`frob.gitio.run_argv` argv position without an intervening
validator-shaped call or a preceding literal `--` terminator is a
command-injection-adjacent trust-boundary finding. Each finding is a
`TaintFinding` (source line, sink line, variable, sink call). Disclosed
scope cuts: literal-argv sinks only, no interprocedural flow (phase 2 per
T-0781's body); WARN-tier at first turn-on per the T-0688/T-0973
promotion precedent.
