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
| env | os.environ/process.env/std::env reads |
| ffi | ctypes/cffi/NAPI/unsafe extern |
| native | compiled artifacts in the wheel/crate (opaque to scanning) |
| install-hook | setup.py/build.rs/postinstall scripts containing any of the above |
| obfuscation | decode-then-eval chains, high-entropy string blobs, minified-source-in-sdist mismatch |

`native` and `obfuscation` are capabilities in their own right: compiled
code cannot be vetted statically and is therefore trusted only by explicit
declaration (`native = ["pydantic-core"]`); obfuscation signals are never
declarable -- they are VET004 errors, full stop.

## JavaScript/TypeScript: first-priority ecosystem

npm is where the attack volume is (the 2024-2026 waves ran overwhelmingly
through npm lifecycle scripts and typosquats), so the JS/TS path gets
first-class treatment, not parity:

- **All four lockfiles**: package-lock.json, pnpm-lock.yaml, yarn.lock,
  bun.lockb (binary -- parsed via `bun bun.lockb` text dump adapter).
- **Lifecycle scripts are the headline capability**: preinstall/install/
  postinstall/prepare in any package.json in the tree map to
  `install-hook` and are DENIED BY DEFAULT -- a lifecycle script needs an
  explicit `[vet.allow]` entry naming it, mirroring the
  `--ignore-scripts` discipline hardened orgs already run. vet also
  verifies `ignore-scripts=true` is set in .npmrc when `[vet].enforce`
  is on (belt and suspenders; VET-JS001).
- **Dependency confusion (VET-JS002)**: any dependency whose name matches
  an internal/scoped pattern (`[vet].internal_scopes`) but resolves to
  the public registry, or whose registry URL differs between lockfile
  entries, fails.
- **Typosquat distance (VET-JS003)**: new dependency names within edit
  distance 1-2 of a top-N npm package (bundled list, refreshed with
  `--sync-advisories`) require explicit confirmation in [vet.allow].
- **Non-registry sources (VET-JS004)**: git/http/file dependencies in
  the manifest are declarable-only, never silent.
- **Integrity fields**: lockfile `integrity` shas are cross-checked
  against scanned artifacts (feeds VET006).

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

## Mechanics

- **Input**: the lockfiles frob already understands the shape of
  (uv.lock/poetry.lock, Cargo.lock, package-lock.json/pnpm-lock.yaml) --
  name, version, artifact hash per dependency.
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
| VET009 | stylometric self-similarity | new code in version N+1 is structurally alien to the package's own history -- reuses the frob-core WL-kernel/fingerprint machinery from docs/dup.md pointed at "this package vs itself over time" |
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

Prior art is embraced, not reimplemented: GuardDog, pip-audit/osv-scanner,
OpenSSF Scorecard, and sigstore run as adapters (see above). frob's
first-party differentiators: declaration-vs-observation conformance (not
advisory output), version-escalation diffs as the primary signal,
cross-language capability sets via one grammar stack, offline-first, and
gate enforcement.

## Public API

```python
# frob/vet/__init__.py
def scan_tree(root: Path, cfg: VetConfig) -> Result[VetReport, VetError]
def capability_diff(prev: PackageVerdict, cur: PackageVerdict) -> tuple[str, ...]

class PackageVerdict(BaseModel):   # frozen; content-addressed by hash
    name: str
    version: str
    artifact_hash: str
    capabilities: frozenset[str]
    signals: tuple[str, ...]       # obfuscation/install-hook details

class VetReport(BaseModel):        # frozen
    verdicts: tuple[PackageVerdict, ...]
    violations: tuple[Violation, ...]   # VET001..VET006, gate-shaped

class VetError(ErrorSet):
    LockfileUnsupported = "No parser for this lockfile format"
    SourceUnavailable   = "Package source not in local caches; rerun with --fetch"
    CacheCorrupt        = "vet cache unreadable; delete .frob/vet.db to rebuild"
```

## Sequencing and integration

- Phase 9 (0.2.x), after frob-core lands (capability queries are cheap,
  but sdist walking wants the incremental cache infrastructure matured).
- CLI: `frob vet [--fetch] [--json]`; gate stage in `frob check` when
  `[vet].enforce = true`.
- Supersedes the earlier "POL kind=dependency" idea: license and pinning
  checks fold into frob.vet as VET-family rules rather than a parallel
  policy kind.
