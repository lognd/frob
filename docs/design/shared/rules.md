# Rules, gates, and the check pipeline

Status: current
Owner: gob
Decisions: D3, D32, D88, D89, D21, D28, D45, D107, D106, D98, D103, D122
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Ownership after charter.md: the rule framework (sections 1, 2, 5, 6) is `gob-rules`; family ownership between frob and grimble is in charter.md. Inputs: notes/v1/gates-and-rules.md (667 rule
ids behind ~72 gate functions; 145 keep, 144 merge, 378 drop).

## 1. Decisions in one screen

- A rule is ONE Rust item with a derive. Id, family, default severity,
  summary, long doc, fixability tier, polarity, needs, and the docs page
  are all generated from it. There is no 580-line `[gates.severity]` table; a
  repo overrides severity per rule only when it disagrees with the
  default.
- Two rule tiers: universal rules run over the universal structural
  model U (universal-model.md) for every language; language rules run tree-sitter queries or patterns against
  one grammar. Both declare themselves the same way.
- One pass. A check run assembles one snapshot (files, parse artifacts,
  U terms, graph, tickets, lock, diff, test collection) once, then each rule
  is a pure function from the snapshot (or a per-file slice of it) to
  findings. No rule walks the tree itself.
- Incremental and cached per file, not per tree. Findings for a file
  are persisted keyed by `(file digest, rule id, rule version,
  side-input digest)`. Repo-wide rules (cycles, dead symbols, dup)
  declare `scope = Repo` and add a graph digest to the key. The cache is
  per worktree (docs/design/shared/architecture.md section 2), which is what "warm" means.
  `grimble check` also caches its binding summary on the warm path: the
  rows of B as document items, the SYS findings and the subject counts.
  The key is the path and content digest of every walked file, the
  `grimble.lock` bytes and the `[grimble]` knobs, and the entry is scoped
  by the engine fingerprint plus a digest of the rule tables, so another
  build or another rule table never reuses it. The same rules digest
  (`gob_rules::rules_digest`) scopes every gob-check product's rows
  (`Product::cache_engine`, shared by crunk's prune) and frob land's
  base-findings cache. Directive-scan and extraction caches store facts
  rather than verdicts and are keyed on their extractor versions only. Any change
  to a walked file, the lock or a knob is a miss. `grimble ack` still
  builds the full binding.
- Severity enum is `Error | Unresolved` (Warn and Advisory are removed,
  section 6.1; text below describing them is the running code until
  ~BA6CSGY lands); the exit
  code follows the table in docs/design/shared/cli-contract.md section 2 (findings alone never fail
  a run; `--fail-on` does, and a required Unresolved does under
  `[check] fail_on_unresolved`, the one mechanism in docs/design/shared/cli-contract.md section 2);
  "unmeasured is not zero" kept (a rule that could not evaluate reports
  Unresolved and that is visible).
- Bind before own (lint-catalogue-2026-10-08 section 3.2). When a
  maintained tool has a documented rule for the shape, a `[[check.tool]]`
  stage with an id map binds it, and frob owns a rule only when (a) it is
  the cross-file or universal version the model sees better, (b) the
  language has no such tool, or (c) it needs frob context (tickets,
  leases, the grimble model, hot roots). Type-aware linters (typescript-eslint
  with type information, pyright, `dotnet build` analyzers) run as a separate
  stage outside the 2 s budget and are timed separately.
- Precision before on (section 6.1.3). A new rule ships as an Error with its
  existing findings baselined, or `default = off` when its evidence row is
  contested, until the precision ledger (N16) shows its not-useful rate
  under the ceiling.
- Exceptions (rules.md), ratchet pools and fix tiers A/B/C are
  kept; quarantine is Milestone 2 or later (D36). Profiles collapse to
  two knobs (section 7).

## 2. Declaring a rule

```rust
#[derive(Rule)]
#[rule(
    id = "COV001",
    family = Coverage,
    severity = Error,
    tier = Universal,             // Universal | Lang
    scope = File,                 // File | Repo
    fix = Manual,                 // Manual | Deterministic (tier A) | VerifyCommit (B) | FixIt (C)
    polarity = P-,                // P+ | P- | P0 | Pn | Pc (required; universal-model.md 4.2)
    needs(Q::PublicApi, Q::Doc),  // the queries the rule reads (universal-model.md 5)
    must_measure = false,         // true: zero subjects examined is a required Unresolved
    needs = Structural,           // optional; Lexical: reads only text, so it needs an opaque-region fire case
)]
/// A public symbol has no doc anchor describing it.
///
/// ## Why this matters
/// ... (markdown; becomes the generated rule page)
///
/// ## Remedy
/// Add `frob:doc docs/<module>.md#<anchor>` above the symbol, or
/// `frob:describes <symref>` in the doc.
struct PublicSymbolUndocumented;

impl Rule for PublicSymbolUndocumented {
    fn check(&self, cx: &Cx, unit: Unit) -> Findings { ... }
}
```

`polarity` is required and `needs(...)` replaces the earlier coarse
`inputs(...)` list: the framework intersects `needs` with the adapter's
capability declaration, decides applicability per file before the rule
body runs, and applies the polarity table of universal-model.md 4.2, so
a rule author cannot forget the Unresolved path. A rule outcome and a
`Finding` carry `subjects_examined`, the rule's Unresolved sites and an
optional `source_rule` (the foreign tool's own id when the finding came
from a bound tool stage, section 4).

Generated by the derive: the `RuleMeta` static (registered through
`inventory`; it carries polarity and needs), the `RuleId` enum arm and
its `FromStr`, the rule page and its index row, with polarity and needs
rows (paths in notes/research/documentation.md section 3), the JSON schema
entry for `[rules.<id>]` config, a generated mdtest with one firing and
one non-firing case plus, for a universal rule, a third fixture in a
language that lacks the feature, expecting Unresolved or a
not-applicable listing and never clean (the positive-control and
pair-fixture doctrine, extended to three: a rule whose doc example has
no non-firing case does not compile), and the
test that the long doc has a Remedy section. A rule without a `## Remedy` section fails to compile.

Adding a rule is therefore one file in the crate that owns its family
(docs/design/shared/charter.md section 2.5).
Removing one deletes that file; nothing else references the id as a
string literal. v1's GATERULE/REG010/DOCENUM-on-rule-lists drift locks
vanish by construction.

Universal rules read U (docs/design/shared/universal-model.md section 2 and 5: operators,
role attributes, the query interface) and the callee vocabulary held in
gob-ir, keyed by language. Language rules embed a
tree-sitter query (`.scm`) or a pattern string next to the struct;
the derive checks the query compiles against that grammar at build
time (test generated per rule).

## 3. Rule families carried into v2

Family names stay so that exceptions converted from consumer-repo
waivers port. Ids are `FAMILYNNN` in every product (a family is 2 to 12 uppercase
letters or digits, the first a letter, so `SYSDESIGN101` is valid), with an optional
slug alias (`SYS003` and `SYS-UNDECLARED-FLOW`); ids inside a family are
renumbered only where v1 ids were duplicates or collapsed, and the v1 to
v2 id map is many-to-one where a family collapsed (SYS's 51 ids become a
few parametric ones). The map ships in `docs/migration/rule-ids.md` and
`frob migrate exceptions` rewrites waivers. The authoritative
family-to-crate table is docs/design/shared/charter.md section 2.5; this table gives
scope and content.

| Family | Scope | Carried (from KEEP + MERGE in the notes) |
|---|---|---|
| DRIFT | graph+lock | stale ack, dangling endpoint with rename candidates |
| AFFECT | graph+diff | dependent doc / dependent symbol not touched |
| COV | graph+tickets | undocumented public symbol, unticketed change, missing evidence, private-reach warning (with public callees now real edges) |
| PARSE, DSL | parse | partial parse salvaged, malformed directive (one id each, parametric; emitted under the namespace of the product that parsed the file) |
| CYCLE, ARCH, LARGE, DEAD, DUP | repo | import cycles, a small metric core (size, nesting, LCOM, coupling, layering), dead symbols, clone rungs R1-R5 |
| TODO | code | bare TODO/FIXME, todo pointing at closed ticket |
| SCOPE, PRE, QUEUE | tickets+diff | out-of-lease write, pre-work sweep, queue hygiene |
| INV | graph+invariants | invariant without anchor/evidence, forbidden import, property test required |
| TEST, TDD | tests+coverage | binding resolves, floors, stamp freshness, commit-order |
| DOC, DOCENUM, NEGEXIST, REF | docs | anchor resolves, command blocks resolve, enumerations match, absence claims expire, references back |
| TICK, MILE, CROSSTICKET | tickets | ledger integrity, milestone tail, cross-ticket leakage |
| DEPR, REL, VERSION | code+release | sunset, unbumped API, version authority (the changelog-fragment check is REL003 only) |
| EXC | findings | reason, can-never-match, over-broad, stale, reattest, expiry, budgets (docs/design/shared/rules.md section 10.6) |
| NARR | comments | ticket narrative in comments (notes/research/documentation.md section 4) |
| CFG | config | a materialized knob is missing (docs/design/shared/architecture.md section 1.6) |
| REG, DEC | registry | enforces-site present, decision implemented |
| SIB | frob | sibling unavailable: SIB001 `sibling-unavailable` (docs/design/shared/sibling-contract.md section 6), one required Unresolved per configured product with a reason of `absent`, `incompatible`, `failed`, `timeout` or `malformed`; ids SIB001-SIB099; owner frob, crate frob-check |
| PACK | grimble | data packs and the registry drift-lock: PACK001 lock mismatch, PACK002 unknown atom, PACK003 detector unavailable, PACK004 duplicate, PACK005 malformed pack, PACK006 pack unavailable, PACK007 unknown infer rule, PACK008 redundant override (docs/design/shared/packs-and-plugins.md section 12.9); ids PACK001-PACK099; owner grimble, crate grimble-capabilities |
| MDL | grimble | .grmb well-formedness: MDL000 lexical and parse errors, MDL001-MDL021 (docs/design/grimble/grmb-spec.md section 11 table: includes, headers, names, selectors, types, exceptions, V-model, atoms, duplicate clauses, roots) and MDL022-MDL034 (planning match exhaustiveness, error handling, hop typing, arm reachability, termination, retry, wildcard arms, scenario start, requires cycles, planning structure, and the later planning additions; the one table is docs/design/grimble/grmb-spec.md section 16.1, so MDL001-MDL034 are all defined there); ids MDL000-MDL099; owner grimble, crate grimble-model |
| PLAN | grimble | planning obligations, coverage and waypoints: PLAN001-PLAN022 and PLAN027 (goals, steps, impls, evidence, arms, ratchets), PLAN030-PLAN034 (waypoint chains), PLAN040, PLAN041 unmapped error, PLAN042 unproducible mapping, PLAN044 open map without `_` (the outcome-map rules; PLAN043 is retired into PLAN006) and PLAN050-PLAN052 and PLAN056-PLAN058 (verification; PLAN053-PLAN055 and PLAN059 are retired into the frob-side PM046-PM049); PLAN001 to PLAN010 are implemented as rule files in grimble-bind (`plan001.rs`/`.md` and so on, evaluated from the planning graph in `plan::findings`; PLAN004 skips an empty selector, which SYS004 owns, and PLAN005 is Unresolved when only a May selector could supply the evidence; PLAN006 fires once per collected (step, variant) pair of a scenario that no resolving `verified_by ... for STEP.VARIANT` on the scenario or on an impl of the step covers, Unresolved when only a May selector could, waypoints being unmodeled; PLAN002 and PLAN010 read the scenario `realizes` and `include` edges; PLAN007 checks the realization kinds against the affordance rule of the step owner, taking a scenario trigger from its first main-chain step, and is Unresolved when that trigger is unknown; PLAN008 walks `from` edges out of the `entry` pages; PLAN009 compares `in node` with the Must owner of each bound realization, waypoints being unmodeled; the spec table lists PLAN002 and PLAN007 to PLAN010 as Warn and PLAN006 as Advisory but the severity model has no Warn, so they report as Error); PLAN012 (non-ok arm ending `end ok`), PLAN013 (unused wildcard impl), PLAN014 (unused step, single-variant refinement or `one_of`), PLAN015 (`sorry` hole), PLAN018 (unrealized `one_of`) and PLAN027 (realized `non_goal`) are implemented as rule files in grimble-model and evaluated in its `plan_check` pass over the parsed planning items, all reporting as Error, PLAN018 skipped when the index is degraded; like every rule they are on by default, Advisory having been retired (section 6.1.1), and are turned off per product with `[rules.<id>] severity = "off"`; ids PLAN001-PLAN099; owner grimble, crates grimble-bind and grimble-model; the one table home is docs/design/grimble/grmb-spec.md section 16.2 |
| AMB | grimble | ambient faults: AMB001 missing policy through AMB009 restart of a stateful node (AMB004, AMB008 and AMB009 are evaluated in grimble-model `plan_check`; the spec table lists AMB004 as Warn and AMB008 and AMB009 as Advisory but the severity model has no Warn, so they report as Error; AMB009 reads a node as stateful from `attr stateful;`) (AMB002 and AMB006 retired and reserved) (AMB005 and AMB007 are model-only proxies: they judge the outcome-map source name, not the bound code; see docs/reference/rules/AMB005.md and AMB007.md); ids AMB001-AMB009; owner grimble, crates grimble-bind and grimble-model; the one table home is docs/design/grimble/grmb-spec.md section 16.4 |
| SYS, CAP | grimble | model binds, capability matrix, declared-plus-proven (one parametric rule, not 51); CAP001, CAP002 (evaluated in grimble-bind `caps` from observed callee-vocabulary uses and `may` grants; pack severities and `at` sub-file scopes pending), CAP004 (excused but used, owner grimble-capabilities), CAP005 (a new or widened `may` grant with no attester's approval in `grimble.grants.toml`, evaluated in grimble-bind `grant_ack`); CAP003 is retired (D75), its id is never reused; SYS012 is a matrix-build check implemented in grimble-capabilities (G14) |
| PM | frob | project-management discipline (pm-and-releases.md) |
| SEC, PII, VET | code+deps | secrets, pii structural, dependency vetting |
| BIND | graph | cross-language sig mismatch, missing counterpart |
| NEAT | code | the neatness family, NEAT001-NEAT037 (grimble/rule-families.md): honesty and effects, one level of abstraction, caller-friendly signatures, thin hooks; owner grimble, crate grimble-lints |
| CI, DK | ci | CI001-CI015 over GitHub Actions and DK001-DK004 over Dockerfiles (grimble/rule-families.md); owner grimble, crate grimble-ci; tool-bound findings arrive through `[[check.tool]]` stages |
| POL, GPOL | config | user-declared policy rules: `POL` over tickets and docs from `[[policy]]` in `frob.toml`, `GPOL` over code from `rules/*.grl.toml` next to `grimble.toml` |
| PATH | code | host-path portability (section 3.1): PATH001 absolute host path literal, PATH002 separator literal applied to a path turned into a string, PATH003 host path pasted into a command-line string; owner grimble, crate grimble-lints; universal over U |
| ERR | code | error handling: ERR001 empty error handler, ERR002 discarded fallible result (Unresolved when the callee's fallibility is Unknown), ERR003 catch-all that neither rethrows nor logs; owner grimble, crate grimble-lints; ERR001-ERR003 are grimble-lints code rules only (the planning outcome-map rules that once shared these ids were renumbered to PLAN041, PLAN042 and PLAN044); universal over U; bound ruff BLE001/E722/S110/TRY and Roslyn CA1031 map here |
| TESTQ | code | test-body hygiene: TESTQ001 test without assertion, TESTQ002 sleep, wall clock or unseeded rng in a test, TESTQ003 control flow in a test body (off by default); owner grimble, crate grimble-lints; Advisory until measured |
| PAIR | code | acquire without release on the teardown path (resources, subscriptions, timers, handles): PAIR001 with per-language vocabulary packs (Rust Drop, C# using/Dispose, Unity OnEnable/OnDisable, React effect cleanup, Go defer); owner grimble, crate grimble-lints; relates to PROTO (lint-requirements R20) |
| TYPING | code | type strictness and boundary casts: TYPING001 strict checking disabled in project configuration (Advisory; one finding per site naming the key to set, from `grimble_lints::typing::check`), TYPING004 unvalidated cast of network or file data; bound `any`/unsafe-cast lints map here; owner grimble, crate grimble-lints (TYPE is crunk's typography family and is not reused) |
| VIS | repo | visibility wider than its uses: VIS001 (Advisory), binds rustc `unreachable_pub` where present; owner grimble, crate grimble-arch |
| FMT, SPELL | tool | bound only: FMT001 formatter check mode (fix tier A, only inside the ticket scope), SPELL001 typos (Advisory, honours typos.toml); owner frob, registered in the frob-check registry. v1 FMT001/FMT002 were directive-format ids folded into PARSE, so `docs/migration/rule-ids.md` must not alias them to the new FMT001 |
| NAME, LINT | tool | bound only, grimble namespace: NAME naming conventions (ruff N8xx, IDE1006, naming-convention); LINT ranges 0xx idiom, 1xx perf idiom (bound perf is LINT1xx because PERF001 is engine timing), 2xx correctness, 3xx concurrency, 5xx leftover debug |
| REACT | tool | bound only, grimble web pack: react-hooks and eslint-plugin-react findings |
| UNITY | code+tool | UNITY0xx stays .meta/GUID, UNITY1xx bound Microsoft.Unity.Analyzers, UNITY2xx own hot-context rules (Advisory), UNITY3xx own input and physics rules; unity pack (code-model.md) |
| TIME | code | time and zone discipline (section 3.2): TIME001 local or naive current-time read whose value is stored, compared or sent, TIME002 naive and aware datetime mixed, TIME003 test date literal against code that reads the wall clock; owner grimble, crate grimble-lints; universal over U |

### 3.1 PATH: host-path portability (D86)

The `/` versus `\` difference broke this repository's CI on every first
Windows run (merge driver path, command allowlist, `--cwd` comparison,
test fixtures). Clippy has no lint for it and the Windows-target clippy
check only catches code that does not compile. PATH catches code that
compiles everywhere and is wrong on one platform. It is the second line
of the path discipline in architecture.md (types, compile-time confinement and
both-style tests come first) and the product feature that brings that
discipline to other repositories. It is a new family:
v1's `PORT` (frob policing its own package paths) is dropped and its id
is not reused, so converted v1 waivers keep their meaning.

| Rule | Fires on | Default |
|---|---|---|
| PATH001 `absolute-host-path` | a string literal that is an absolute host path: `/home/<name>/`, `/Users/<name>/`, `/root/`, `/tmp/...`, a drive path `X:\` or `X:/`, a UNC path; not `/`, URLs, shebang lines, or entries in `[path] allowed` (default `/dev/null`) | Error in non-test code, Advisory in tests and fixtures |
| PATH002 `string-path-separator` | a value produced by turning a path into a string (Rust `to_str`, `to_string_lossy`, `display`, `as_os_str`; Python `str(p)`, `os.fspath`; per-language through the callee vocabulary) that is split, joined, concatenated, compared, trimmed or searched with a literal `/` or `\` in the same function | Error |
| PATH003 `path-in-command-line` | a path-derived string interpolated into one command-line string (`format!` into a shell command, `sh -c`, a git config value that git runs, a `.ps1` body) instead of passed as its own argument | Error |

Remedies name the portable form: `Path::join`, `components`,
`strip_prefix` and `Path` equality; the repository-relative path type
(forward slashes by contract, sibling-contract.md) for paths stored in
data; one argument per path for commands, with the platform's quoting
helper where a single string is unavoidable. A path that is *meant* to
use `/` (a repository-relative key, a URL path) goes through that type,
so PATH002 stays quiet on it without an exception. PATH002 and PATH003
need def-use within one function, so they are GRL relational rules in
the standard pack and among the first written in GRL (grl-spec.md); a
language whose adapter lacks the path-conversion roles reports
Unresolved, never clean. This repository raises PATH002 and PATH003 to
Error in its own config.

The detectors live in `grimble-lints::path` (`scan`): PATH001 reads
string literals of Rust, Python, TypeScript and C#; PATH002 and PATH003
run a per-function name-based def-use taint for Rust and Python (the
languages with path-conversion roles) and list both as unresolved for
every other code language. The corpus under
`crates/grimble-lints/tests/corpus/path` holds the ~G5RJY40 Windows bugs
and their fixed versions.

### 3.2 TIME: one clock, one zone (D93)

~AAZFNR5 turned CI red at 00:06 UTC: cycle state used the UTC day, the
library's "today" used the local zone, and a test's hardcoded future
date became today. TIME is the second line of the time discipline in
architecture.md (typed instants and days, one injected clock, clippy
confinement come first) and the product feature that brings it to other
repositories.

| Rule | Fires on | Default |
|---|---|---|
| TIME001 `local-clock-read` | a current-time read in the local zone or without a zone (Python `datetime.now()` without `tz`, `date.today()`, `datetime.utcnow()`, `time.localtime()`; JS `new Date()` read through local getters; Rust `chrono::Local::now`, `jiff::Zoned::now`) whose value is stored, compared, serialized or sent, not only displayed | Warn |
| TIME002 `naive-aware-mix` | arithmetic or comparison between a naive and a zone-aware datetime, or parsing a timestamp without a zone into a value later compared with an aware one | Warn |
| TIME003 `test-date-vs-wall-clock` | a test that builds or asserts a calendar date or timestamp literal while the code it reaches reads the wall clock with no clock injected | Advisory; Unresolved where reach is undecided |

Remedies name the portable form: one UTC instant type for anything
stored or compared, one day type with a documented zone, a clock passed
in and read once per operation, local time only for display, and test
dates built relative to the clock (or a fixed clock in the test).
TIME002 and TIME003 need def-use and reach, so they are GRL relational
rules in the standard pack; a language whose adapter lacks the
clock-read roles reports Unresolved, never clean. This repository raises
TIME001 and TIME002 to Error in its own config.

Implemented (~8KVQQN5): TIME001 and TIME002 ship in `grimble-lints`
(`time::scan`, the `time_pass` product pass) as syntactic per-scope
detectors for Rust and Python, not GRL rules: a name-based def-use inside
one function or module body decides whether a read is only displayed, and
which names hold naive or aware values. Import aliases are resolved. A
walk with TypeScript or C# files reports each rule Unresolved once per
language (no clock roles); a walk with no Rust or Python file is not
applicable. Both default to Warn. The repository scan over its own Rust
and Python files finds no site, so the Error raise is applied in this
repository's `grimble.toml` (`[rules.TIME001]` and `[rules.TIME002]`,
`severity = "error"`).

Implemented (~7YMB3EQ): ERR001 `empty-error-handler`, ERR002
`discarded-result` and ERR003 `silent-catch-all` ship in `grimble-lints`
(`err::scan`, the `err_pass` product pass) and run in `grimble check`.
ERR001 covers Rust, Python, TypeScript and C#; ERR002 is Rust only
(`let _ = call()`); ERR003 covers Python, TypeScript and C#. A Certain
site is a Warn; an ERR002 site whose callee fallibility is not readable
in the file is Unresolved (fidelity), never a guessed Warn. Languages
the scan does not read (JavaScript, TSX) are not judged, and a walk with
no qualifying file makes the rule not applicable. Each rule has a page
(`crates/grimble-lints/src/rules/err00N.md`) with fire and clean cases
(and an unresolved case for ERR002) and appears in the generated rules
index. They ship with `since = "0.532.0"`; the severity
model is in section 6.1.

Implemented (~CPBVHQF): RES001 `unpaired-resource-acquisition` ships in
`grimble-lints` (`res::scan`, the `res_pass` product pass) and runs in
`grimble check`. It reads TypeScript, TSX, JavaScript and JSX for an
acquire call (`performance.mark`, `Map.set`, `setTimeout`,
`setInterval`, `addEventListener`, `URL.createObjectURL`,
`new AbortController`) with no paired release (`clearMarks`, `delete`,
`clearTimeout`, `clearInterval`, `removeEventListener`,
`revokeObjectURL`, `abort`) in the pair's scope (file, class or
function, per the pairs table; same receiver where the API needs it). A
Certain site is a Warn; a site whose handle is used elsewhere in scope
or discarded, so a release may live out of sight, is Unresolved
(fidelity), never a guessed Warn. A release in another scope or on
another receiver does not pair, test bodies are
exempt, and other languages are not judged; a walk with no script file
makes the rule not applicable. The report is cached under `res-v1`. The
rule has a page (`crates/grimble-lints/src/rules/res001.md`) with fire,
clean and unresolved cases and ships with `since = "0.532.0"`; the severity
model is in section 6.1.

Implemented (~G59GJ01): PAIR001 `acquire-without-release` ships in
`grimble-lints` (`effect::scan`, the `pair_pass` product pass) for React
effects in TypeScript, TSX, JavaScript and JSX: a `useEffect`,
`useLayoutEffect` or `useInsertionEffect` that starts a timer, listener,
request, observer or subscription and returns no matching cleanup is a
Warn; a cleanup returned only under a branch, or one the scan cannot read,
is Unresolved. A walk with no such file is not applicable. The Unity
vocabulary (`unity::scan`) and other languages are not wired yet.

Implemented (~9XDR1GY): UNITY201 `lookup-in-hot-code` and UNITY202
`allocation-in-hot-code` ship in `grimble-lints` (`unity_hot::scan`, the
`unity_pass` product pass). Both are Advisory and run only on C# files that
mention `UnityEngine` or `MonoBehaviour`; a lookup (`GetComponent`, `Find*`,
`Camera.main`) or managed allocation reachable from `Update`, `LateUpdate`,
`FixedUpdate` or `OnGUI` fires, while a lookup cached in `Awake`, `Start` or
`OnEnable` stays quiet. A walk with no Unity C# file is not applicable.

Implemented (~T08HTWJ): UNITY301 `legacy-input-under-input-system` and
UNITY302 `physics-force-outside-fixed-update` run in the same `unity_pass`
product pass (`analyze_project`, called through `analyze_all`). Both are
Warn. UNITY301 reads `activeInputHandler` from the nearest
`ProjectSettings/ProjectSettings.asset` above each C# file (so several
projects in one repo each follow their own settings) and fires only for
handler `1` (Input System only); `0` and `2` are clean. A file under no
readable `PlayerSettings` asset is not examined, and a walk with none is
not applicable. UNITY302 needs no settings and fires on a Rigidbody force
or move made from `Update` or `LateUpdate`.

The grimble check reads `[rules.<id>] severity = "error" | "off"` (`RuleOverrides` in `grimble-check`; "warn" and "advisory" are config errors naming the replacement).
The frob product reads the same table from `frob.toml`: `[rules.<id>] severity = "off"` (or `disabled = true`) drops that rule's findings after the run (`drop_disabled_product_findings` in `gob-rules`), `"error"` is accepted, and `"warn"`/`"advisory"` are config errors. This repository turns off the rules that still have findings, each with a `reason` naming its burn-down ticket, until the baseline store lands (6.1.7).
The override beats the rule default. An unknown rule id is logged and ignored
because `[rules]` is shared with other products; an invalid token fails
the run. Unresolved findings are never re-graded, and `disabled` is not
read by grimble. The table is hand-parsed, so it is not part of the
generated `docs/reference/config/frob.md`.

Moved out of frob core (D88, refined by D89, owner decisions 2026-10-04),
split by the charter.md boundary (grimble models systems and code in any
language; crunk models the rendered front end): to crunk as packs, A11Y,
SEO, LAUNCH and the markup and asset part of WEBPERF; to grimble as packs,
WEBSEC (joining the SEC security family), SQL, COMPLY (with PII), ROUTE,
the server part of WEBPERF, and the STORE/SYSDESIGN/GRAMMAR system-design
family. All are packs on the public pack mechanism (D76), not core.

Dropped from core (optional packs or gone):
PERF lexical set, EXHAUST/FFI/SUPPRESS/CONFIGPATH/PKG/NATIVE/PORT/
LEXCHECK/CLAUDE/WIRE003, every `*SCHEMA001` (serde `deny_unknown_fields`
does it), typestate PROTO unless a consumer commits.

Policy rules (POL) are the user-extensible tier, and the owner wants
them to feel natural and powerful for both per-language and universal
linting (2026-10-02). Three authoring levels share one registry and one
output:

1. Declarative rule files, `rules/*.grl.toml` next to `grimble.toml`
   (and `POL` ticket/doc predicates under `[[policy]]` in `frob.toml`),
   in the ast-grep shape. Milestone 2 or later (D36):
   a `pattern` with metavariables (`$X`, `$$$ARGS`) written in the
   target language's own syntax, combinators `all`, `any`, `not`,
   `inside`, `has`, `follows`, `precedes`, `regex`, `kind`, plus
   constraints on metavariables and an optional `fix` template.
   Example, Python only:

   ```toml
   id = "GPOL001"
   alias = "no-print-in-lib"
   language = "python"
   severity = "error"      # TOML spells the Severity enum in lowercase
   message = "use the module logger, not print"
   rule = { pattern = "print($$$ARGS)", not = { inside = { kind = "decorated_definition", has = { pattern = "@cli" } } } }
   fix = "_log.info($$$ARGS)"
   ```

2. Universal rule files, same syntax, `language = "*"`, where
   `pattern` and `kind` address U operators and role attributes
   (universal-model.md 2.3 and 2.4) instead of a grammar:
   `rule = { kind = "group", role = "loop", has = { kind = "apply",
   role = "call", callee = "sort" } }` (a loop is the role `loop` on a
   `group` node; a call is `apply[kind=call]`), with callee names
   resolved through the per-language callee vocabulary. One file, every
   language whose adapter provides the roles; the same rule runs on
   Python, Rust and TypeScript, and an adapter lacking them is
   Unresolved for that language, never clean.

3. Rust rules (`#[derive(Rule)]`) for anything needing resolution,
   cross-file state, or the graph.

Declarative rules are compiled at load into the same `RuleMeta` and
run on the same per-file memo as Rust rules, get the declared
`FAMILYNNN` id and optional slug alias, appear in the generated rule
reference, and are
tested with the same markdown corpus format (`frob rule test` runs the
cases embedded in the rule file; examples may carry `config` (a TOML
subset: tables, arrays of tables, strings, string arrays), `diff` and
`lease` inputs, and a rule with `lang -` needs no example language; a
`fire` example with only side inputs passes iff the rule reports, and
findings with no source node are reported at line 0; an example in a
language the capability matrix does not model is not applicable to a
`lang *` rule). Engine: `ast-grep-core` for the
grammar level, with the U level implemented on the same matcher trait
so combinators behave identically. Status, stated once: version
compatibility is answered (D42, ast-grep-core 0.45.3 against the
workspace tree-sitter pin); the remaining spike is an ast-grep `Doc`
implementation over U terms; the spike is decided: level 2 uses the in-house matcher of
`gob-pattern` (kind, role, callee, all, any, not, inside, has), no `Doc` trait (G17a).
Level 1 grammar patterns (G17b) are implemented in `gob-pattern`'s `grammar` module: a
pattern is parsed with the target language's own tree-sitter grammar, `$X` binds one node
and `$$$ARGS` binds zero or more siblings, a `fix` template splices the captures back in
(`grammar::render`), and `grammar::apply` applies the resulting edits to the source.
`RuleFile::find_source` runs a rule over source text and returns its findings. A rule
authored at level 1
can be promoted to level 2 by changing `language`, and to level 3 by
`cargo dev scaffold-rule`, keeping its id and tests.

## 4. The check pipeline

```
frob check [--files F..] [--ticket ID] [--base REF] [--only FAMILY..]
           [--fix | --fix-all] [--delta] [--fail-on SEV] [--json | --sarif] [--timing]
```

1. Load config (`frob.toml`, deny unknown fields), open the repository's
   shared cache (`<git common dir>/frob/cache/frob/cache.sqlite`, one per
   repository, shared by the primary checkout, every ticket worktree and the
   land ratchet's base worktree; keys are content digests, so sharing is
   safe; outside a git checkout `.frob/cache.sqlite`).
2. Discover tracked files (`ignore` crate honoring .gitignore), stat,
   digest changed ones (blake3, rayon).
3. Build the snapshot: parse artifacts, symbols, edges, resolved graph,
   tickets, lock, diff vs base, test collection (U terms from milestone 2).
   Each step is memoized on its inputs in the cache; a one-file change
   re-derives only that file's artifacts and the global joins.
4. Select rules: all by default, including sibling products' families
   when configured; a configured sibling that is missing or whose
   `--json` has another `schema_version` (or `[compute]` digest) yields
   one Unresolved finding per product, marked `required` (cli-contract.md
   section 2). `--only` by family or id; `--ticket` adds the ticket's
   scope-and-lease context and narrows per-file rules to the ticket's
   files plus `[check] ticket_hops` (default 1) hops of dependents; this
   is the only definition of `--ticket` scoping (v1 land's rapid
   `--files` logic, now the default for scoped runs). The scoping is a
   lower bound: an Unknown edge out of a touched symbol (a call the
   graph could not resolve) yields one Unresolved ("selection
   incomplete: N unresolved call sites") and widens the run to the
   file's crate, so a dependent behind dynamic dispatch is never
   silently outside the run.
5. Run rules in parallel (rayon), per-file rules over changed-or-
   dependent files, repo rules once. Findings are canonical-ordered
   (rule, file, line, message) so output is byte-stable.
6. Post-process: exceptions (ticket-bound exits evaluated by frob only,
   from sibling `--json`), ratchet pool, severity overrides, census.
7. Render: text with remedy on every finding, `--json` (stable schema,
   generated), `--sarif` for CI annotations (Milestone 2 or later
   (D36)), `--timing` per rule.
8. Exit per the table in docs/design/shared/cli-contract.md section 2: 0 unless `--fail-on
   <severity>` (or `[check] fail_on`) is set and a finding at or above
   that severity exists, then 1; or unless a required Unresolved
   finding exists under `[check] fail_on_unresolved`, then also 1
   (docs/design/shared/cli-contract.md section 2 defines the mechanism; Unresolved never counts
   toward `--fail-on`).

Removed: the `--only` stage-group chunk dance, `--budget` self-chunking,
the agent full-check refusal, the forkserver pool, admission markers,
the derived-state lock. Targets: warm scoped run under 1s, warm full run
under 2s on 100k lines ("warm" is a fresh process with a populated
`.frob/` cache; docs/design/shared/architecture.md section 2), cold full run bounded by
parse (expect 3-6s). External tool stages are outside the 2s budget and
reported separately. If a real repo exceeds 30s cold, `--budget` is
reconsidered, not before.

Tool stages (ruff, ty, clippy, tsc...) remain opt-in through
`[[check.tool]]` entries and run concurrently with rules through the
`gob-exec` bounded job pool; frob parses
their output into findings (the parsers live in
`crates/gob-check/src/tool_parse.rs`, owned by gob-check, so both products
share them; frob-check supplies the stage configuration) so one
report covers everything. The parser list: SARIF 2.1.0, cargo JSON
diagnostics (rustc and clippy), ruff JSON, ESLint JSON, typos JSON,
formatter check mode (rustfmt, ruff format, prettier, dotnet format, gofmt,
clang-format; one finding per file) and stylelint JSON, alongside the
zizmor and actionlint parsers that exist today. Type-aware linters are a
separate stage outside the 2 s budget (section 4 targets). A tool stage declares a `parser` and an id
map from the tool's rule ids to frob ids (for example zizmor
`unpinned-uses` to CI001, clippy `too_many_arguments` to NEAT002); the
finding carries the frob id plus `source_rule` (the tool's own id), so
exceptions, severity overrides and the report treat it like any other
finding. A tool's native suppression (`#[allow(clippy::...)]`,
`# zizmor: ignore[...]`) hides the finding before frob sees it, so a
meta-rule (EXC017, docs/design/shared/rules.md section 10.6) flags a native suppression
of a bound rule that has no matching frob exception. A tool stage that
produces no evidence is never silent: an unresolvable program, a failed
`version_args` probe, an exit status the parser does not declare normal
(actionlint 0 and 1; zizmor 0 and 10-14) or output the parser cannot read
is a `TOOL001` Unresolved with required reason `tool-failed`, naming the
stage, the command, the status and an escaped, capped stderr excerpt, so
the default `fail_on_unresolved = "required"` fails the gate. Only
`optional = true` downgrades a missing binary to a non-required
Unresolved. Fix tiers:
A deterministic (rule provides `fix()`), B apply-verify-commit (runs
bound tests), C fix-it only. `--fix` without `--ticket` requires
`--fix-all`, as in v1.

### 4.1 One full check per worktree

Stacked `frob check --ticket` runs in one worktree starve a shared host, so a full run (any
`frob check` without `--only`) takes `.frob/check.lock` in the repository root; the lock holds
the pid, start time and argv of the holder. A second run while the holder is alive is refused
at once with `E-CHECK-CONCURRENT` (exit 3, distinct from the exit 1 of a gate failure) naming
those three. A lock whose pid is dead is reclaimed automatically (the same `/proc` liveness
probe as the land lock). `--allow-concurrent` is the override for a genuinely intended
parallel run: it takes no lock and appends a line to `.frob/check-overrides.log`. `--only`
runs are not locked.

## 5. Exceptions (accept, defer, hotfix, baseline)

Designed in section 10 of this file: one primitive with four kinds, each with a
machine-checkable exit (`accept` re-validated against findings and
symbol digests, `defer` tied to an open ticket, `hotfix` with a hard
expiry, `baseline` pools that only shrink), budgets per component and
age, one reason-quality checker, and the EXC rule family replacing
the v1 waiver and debt rules. Matching modes (symbol-exact, file, package for rules that
declare `waive_scope = Package`) and `waivable = false` on the derive
are unchanged. Every suppressed finding is reported in an `excepted`
section, never dropped.

## 6. Ratchet, baseline, quarantine

- `frob-ratchet.lock.json` (tracked) keeps per-rule baselined finding
  keys (the `baseline` kind in rules.md); baselined findings are muted,
  new ones are Error (6.1.2); pools only shrink. A new rule ships as an
  Error (6.1.3). A finding key is a
  fingerprint: (rule id, symref or file path, hash of the normalized
  message), never a line number, so an edit above a baselined finding
  does not make it new.
- Rule precision ledger (~B2ZBRER). `gob_rules::PrecisionLedger` counts, per
  rule, findings accepted, waived (`defer`, `hotfix`), dismissed, fixed and
  still open. The not-useful rate is `(accepted + dismissed)` over every
  decided finding, in whole percent, and is absent below `MIN_DECIDED` (5)
  decided findings. `frob check --json` reports the run's rows as
  `data.precision`; `demotions(ceiling)` names the rules over a ceiling with
  their numbers. A rule that ships Warn by default needs a measured rate.
  Fixed and dismissed counts persist between runs (~X84157K) in
  `precision-history.json` (`gob_rules::HISTORY_FILE`, `PrecisionHistory`) in
  the product's telemetry directory: the state directory under the root by
  default, which a product may move (crunk keeps it in the shared cache under
  the git dir). The file holds, per rule, the fingerprints left standing by the
  last recorded run, the fixed count, and the dismissals. Nothing locks it: a
  load, change and save is not atomic, so overlapping runs can lose an update
  (the later save overwrites the other's change), and the write itself is a
  plain rewrite, so an interrupted save leaves a malformed file.

  Fixed (the fixed-count rule). Only an unfiltered, unscoped run is recorded.
  A run limited by `--only` or by a scope still reads the history, and the
  ledger gets the persisted counts, but the file is not extended. A recorded
  run compares its open findings with the standing set of the previous record.
  For each rule in its evaluated set (the keys of `subjects_examined`), every
  standing fingerprint that is no longer open and is not dismissed adds one to
  that rule's fixed count, and the rule's standing set becomes its open
  findings. A rule outside the evaluated set adds no fixes and keeps its old
  standing set, unless the run still reports open findings for it, which
  replace that set; so a rule that did not run cannot report fixes. The count
  is of disappearances: a finding that is fixed, reintroduced and fixed again
  counts twice.

  Dismissals. `gob_check::dismiss(product, root, rule, fingerprint, reason)`
  loads the history, records the dismissal and saves it. The reason is trimmed
  and must pass the exception reason checker (`check_reason` with the default
  `ReasonPolicy`): at least 15 characters, none of the banned phrases
  (temporary, temporarily, for now, fix later, wip, todo, tbd, n/a) as whole
  words, and no word repeated back to back. A second dismissal of the same
  fingerprint with a valid reason is a no-op and keeps the first reason. The
  fingerprint is stored as given, not checked against the open findings. A
  dismissed finding that disappears is not counted fixed, and each dismissal
  adds one to its rule's dismissed count. No code path in these modules
  removes a dismissal.

  Failure handling. A history that cannot be read (I/O error or malformed
  JSON) is logged as a warning, and the run's ledger has no fixed or dismissed
  counts; `dismiss` returns the error and writes nothing. A failed save is
  logged and the run goes on. With `skip_telemetry` the whole step is skipped:
  no history is read or written. The `frob doctor` recommendation is not built
  on this yet.
- `--delta` uses a per-checkout `.frob/baseline` of finding fingerprints
  (advisory, untracked), same as v1.
- `frob land` applies the same fingerprints as a ratchet on the base tip
  (~QAFRXM3), comparing like with like: the unscoped check at the head
  against the unscoped check at the base, both with the same options and
  rule set. It refuses a finding at or above `fail_on` only when its
  fingerprint is absent from the base. The base side runs in a throwaway
  detached worktree and is cached per base commit in
  `<git common dir>/frob/land-base/<oid>.json`, shared by every worktree, so a
  second ticket landing on the same base runs no base check (a moved base has
  a new oid, so it is recomputed). The base worktree's check uses the shared
  cache, so every file unchanged since an earlier check is a hit (~TSK0M4Y); the base worktree's `target/` is a symlink to the ticket worktree's, so its
  cargo tool stages reuse the dependency builds of the head checks instead of
  compiling from nothing, which dominated land's wall time in a debug build. The ticket-scoped run still supplies the
  ticket-only findings (SCOPE001, ticket-scoped rules) that no unscoped run
  has, and a repository-level finding such as REL001 is judged only on the
  unscoped side, so text that differs between the scoped and unscoped runs
  cannot make an old tag read as new. Blocking findings already on the base
  are listed in land's report as `pre_existing`, base findings absent at the
  head as `resolved`; nothing is hidden, and `frob check`, CI and release
  status still fail on them. The done guards are about the ticket and are
  unaffected.
- Quarantine and `[land] verify = "ci"` are Milestone 2 or later (D36).
  With a sub-second check, landing runs the full check synchronously,
  so milestone 1 has no post-land red to quarantine, and the
  deferred-verify machinery (queue, watermark, coalescing worker, bisect
  ladder, backpressure, rapid debt) is not built. When quarantine is
  added it needs a CI-result ingestion path (frob-gh), a tracked store
  (`frob-quarantine.json`, never `.frob/`) and a disposition verb
  (file a ticket or dismiss with reason).

### 6.1 No warnings: Error-only severity, the baseline, gate scopes (~BA6CSGY)

Owner policy (2026-10-26): there is no warn severity, only errors. Existing
debt is burned down slowly and visibly. This section supersedes the
Warn/Advisory parts of sections 1, 6 and 7 once the implementation tickets
below land; until then the old text describes the running code.

**6.1.1 Severity.** The enum becomes `Error | Unresolved`, plus `off` as a
configuration value (not a finding severity). `Warn` and `Advisory` are
removed from `Severity`, from `#[rule(default = ...)]`, from `[rules.<id>]`
and `[check] fail_on`. Unresolved stays: it means the rule could not decide,
is never a failure by itself, and fails a run only under the existing
`fail_on_unresolved` mechanism (docs/design/shared/cli-contract.md section 2). A rule is either on
(Error), off (with a recorded reason in its derive or the repo's
`[rules.<id>]`), or Unresolved for a site it cannot decide. "Unmeasured is
not zero" is unchanged. A config that names `warn` or `advisory` is a
config error with a message naming the replacement (`error` plus a
baseline, or `off`), never a silent mapping. Findings that would be Warn
today are Errors that are baselined (6.1.2), waived (6.1.4) or fixed.

**6.1.2 The baseline (replaces ratchet-as-Warn and the ramp-in).**

- File: `frob-baseline.toml` at the repo root, tracked, one per repo (per
  product repo for grimble and crunk, which read the same file under their
  own rule-id namespaces). It supersedes `frob-ratchet.lock.json`;
  `frob migrate` converts the old file once, keeping its keys.
- Format: sorted, one table per rule, so diffs are minimal and merges are
  line-local:

  ```toml
  version = 1

  [rules.PM009]
  reason = "adopting the rule: 438 ready tickets unsized, burn-down ~61BXXNJ"
  ticket = "~61BXXNJ"
  findings = [
    "3f9a1c0d5be2a7aa",
    "9b02e4417c6d10f3",
  ]
  ```

  `reason` and `ticket` (the burn-down ticket) are required per rule table.
  A key is the existing finding fingerprint (`Finding::fingerprint`: rule
  id, symref or file path, hash of the normalized message; digits and
  whitespace are normalized away, never a line number), so an edit above a
  baselined finding does not make it new. No second hashing scheme exists.
- Matching: a finding whose fingerprint is in its rule's list is reported
  in the `baselined` section of the envelope (like `excepted`, never
  dropped) and does not fail the run. Every other Error fails it. There is
  no "baselined is Warn": baselined findings are muted, counted, and shown
  as a per-rule remaining total.
- Shrinking: a key whose finding no longer occurs is removed
  automatically by `frob baseline prune` (run by `frob land` on the
  merge commit's tree so the removal lands with the fix, and by
  `frob check --fix`). Pruning only happens on a full, unscoped run where
  the rule evaluated the key's site (the stale-evaluation rules of
  docs/design/shared/rules.md section 10.3 apply: a skipped rule, version bump or an
  Unresolved site is not stale). A rule table with an empty list is
  deleted.
- Never growing: the only writer that adds keys is `frob baseline adopt
  <RULE> --reason R --ticket T`, which creates a table for a rule that has
  no table and refuses when one exists. It is the single legitimate
  creation event ("tightening a rule creates a new pool"). `check`,
  `land` and `prune` never add. EXC-family rule BASE001 (new) fails a
  check or land when, compared with the base tip, any table gained a key
  or changed `ticket` without `adopt`; a key may be removed with a reason
  by hand, never added. Because land already compares fingerprints
  against the base tip (section 6), a new finding is an Error with no
  baseline needed to catch it.
- Budgets: a table without a live `ticket` (closed, or `dropped` without
  a successor) is BASE002 Error, so debt cannot outlive its plan.
- Merge conflicts: the format is sorted and one key per line, so two
  branches that each remove keys merge cleanly. Two branches that each
  `adopt` the same new rule conflict on the table header; resolution is to
  take either side and rerun `prune` (a union of identical-rule keys is
  legal only if BASE001 sees no net growth over the base tip). A
  conflicted file (markers) is a hard parse error, never treated as empty.
- Concurrent lands: land is serialized per repo (section 4.1 lock) and
  prunes against the base tip it merges onto. A fix that lands after
  another ticket's prune finds its keys already gone and has nothing to
  remove; a landing branch that still lists a key the base already
  pruned is dropped silently (shrinking is monotone). A branch that adds
  a finding of a baselined rule gets a fresh fingerprint absent from the
  base, so it fails as new even though its rule has a table.

**6.1.3 Ramp-in is retired.** `new_rule_warn_releases`, `[rules] ramp`,
`since`-window reporting as Warn, `gob_rules::ramp` and
`ramp_product_findings` are removed; so are `RuleSettings::effective_ramped`
and the `strictness = "warn-new-rules"` value. A new rule ships as an Error.
If it has findings on this repo or a consumer, its author runs `baseline
adopt` in the same change, with a burn-down ticket; "Precision before Warn"
becomes "precision before on": a contested rule ships `default = off`, and
is switched on (and adopted) only when the precision ledger rate is under
the ceiling. `frob release changelog` still lists newly live rules, now
from `since` alone. Consumers upgrading to a release that adds a rule get
the rule's findings as Errors on `frob check`; the release notes list the
`frob baseline adopt` command per new rule, and `frob migrate` prints it.
`strictness` collapses to `strict` (the old value is accepted and ignored
with a deprecation note for one release).

**6.1.4 Heuristic and smell rules are waivable Errors.** Rules that make
a judgment call (families CRAFT, SLOP, COH, DUP, VIS, UNITY; the rule
derive carries `nature = Exact | Heuristic`, default Exact) are Errors a
human may waive. A Heuristic finding message has three parts, always, in
this order:

1. what it is: "HEURISTIC: this is a smell check, not a proven defect.";
2. why it fired: the evidence in one line (what was measured against
   what threshold, or which two sites are similar);
3. the exact suppression, copy-pasteable, at the site:
   `frob:waive COH003 reason="<why this is fine>"`.

Output is audience-specific, chosen by the existing agent-detection used
for hooks (`CLAUDECODE`/`--agent`, never guessed from a tty):

- agent-facing: part 3 is replaced by "Fix the code. Do NOT waive this:
  waiving a heuristic is a human decision." No `frob:waive` text appears
  in agent output for a Heuristic rule, so there is nothing to paste. The
  JSON envelope carries `waivable_by = "human"` and `nature =
  "heuristic"`.
- human-facing: the full three parts, including the waive line.

A waiver is an exception that must carry a reason that passes the
reason-quality checker (docs/design/shared/rules.md section 10.2); `frob:waive RULE` with no
reason, an empty one, or one the checker rejects is itself an Error (EXC
family, existing reason rule) and the waived finding stays live. An agent
authoring a waiver for a Heuristic rule is flagged by the same hook that
detects agent authorship (a human-only waiver is a policy, enforced as
`waivable_by = human` in the envelope and a hook, not by cryptography).
Exact rules are not waivable by default (`waivable = false` unchanged);
they are baselined, fixed or off. Waivers appear in `excepted` and count
against the budgets of docs/design/shared/rules.md section 10.4.

Implementation (~291TPEB): `gob_rules::Nature` (`Exact` default,
`Heuristic`), `Audience` (`Agent`, `Human`), `HeuristicNote::message(audience)`
and `Finding::heuristic(..)` build the three-part message; the fingerprint is
audience-independent.

Wiring (~MXQ4HW5): `#[rule(nature = exact | heuristic)]` (default `exact`)
fills `RuleDef::nature`; `RuleDef::note(evidence)` builds the note for a
heuristic rule. A heuristic `Finding` carries its `nature` and `note`, and
`FindingRecord::from_finding_for(.., audience)` re-renders the message for
the audience and sets the envelope fields `nature = "heuristic"` and
`waivable_by = "human"` (both absent for exact findings). The CLI detects the
audience once per command: any non-empty agent marker variable (`CLAUDECODE`,
`CLAUDE_CODE_ENTRYPOINT`, `CODEX_SANDBOX`, `CODEX_CI`, `GEMINI_CLI`,
`CURSOR_AGENT`, `OPENCODE`, or the explicit `FROB_AGENT`) selects the agent
message; a terminal is never consulted.

**6.1.5 Gate scopes (replace `release_severity`).** A rule declares
`gates = [...]` with a subset of `local | ci | release` (default all
three). A rule runs and can fail only at gates it lists; the gate is
chosen by `frob check --gate <g>` (default `local`; CI invocations pass
`--gate ci`, auto-detected from `CI=true` when unset; `crunk check --gate
release` and `frob release status` use `release`). HUMAN001 and HUMAN002
declare `gates = [release]`: at `local` and `ci` they do not run (their
absence is reported as "not in this gate", not as Unresolved or clean), at
`release` they are plain Errors that block the release (CD) step. The
severity is the same Error everywhere; only scope differs. A repo may
narrow or widen with `[rules.<id>] gates = [...]`; widening a rule to
`local` is allowed, narrowing an Exact rule below `ci` is refused (CI must
see everything that is not human sign-off). `release_severity` is removed
from `#[rule]`, `RuleDef`, `gate_severity` and `apply_gate`, replaced by
`rule_in_gate(def, settings, gate)`; family rows carry `gates` as the
fallback in the same precedence order the old severity used (rule value,
then family). The baseline applies at every gate; a rule scoped to
`release` that has baselined findings does not need them to run locally.

**6.1.6 Edge cases.**

- Other products: grimble and crunk use the same `Severity`, baseline file
  (rule ids are namespaced, so tables never collide), `gates` field and
  heuristic contract; their per-product ramp calls are deleted. A crunk
  release-gate rule that today raises severity at release becomes a
  `gates = [release]` rule or a plain Error.
- Per-repo severity config: `[rules.<id>] severity = "warn"|"advisory"` is a
  config error (6.1.1); `"error"` is a no-op; `"off"` stays and needs a
  `reason`. `[pm] strict` and `[grimble] strict` knobs that select Warn vs
  Error become no-ops (PM and SYS rules are Errors) and are removed after
  one deprecation release. The effective-severity order in section 7 is
  therefore: default, product knob (on/off only), `[rules.<id>]` override.
- HUMAN001/002 are `gates = [release]` (above); the former
  `release_severity` field is gone and their prior "Advisory under check"
  meaning is intentionally dropped, not baselined.
- Unresolved: never baselined (a key is only minted for a decided Error,
  as with EXC016), never waived by a heuristic waiver, and `COV001`-style
  Unresolved burn-down is by measuring (providing the report), not by
  adopt. If a baselined site turns Unresolved it is not pruned.
- Write-time verbs (section 7) refuse when a finding is an Error, which
  is now every finding; a baselined or waived finding does not refuse.
- Exit codes: any non-baselined, non-waived Error fails (exit 1); the
  `fail_on` knob keeps only `error` and `unresolved`.
- Tool-stage findings (`[[check.tool]]`): the id map target severity
  becomes Error or the stage is off; warnings from bound tools are
  baselined through the same fingerprint like any rule.

**6.1.7 Migration order.** Each step is a child of ~BA6CSGY and lands
independently once the mechanism (implementation tickets below) exists.

1. Mechanism first: severity collapse, baseline file and verbs, gates,
   heuristic contract (no rule changes severity until all four exist).
2. Zero-finding rules: every Warn/Advisory rule with no findings on this
   repo (from a full `frob check` per-rule count) becomes Error with no
   baseline. Free, and it stops regressions.
3. Exact rules next, with a small, mechanical fix set: CI010, PM010, PM033,
   SYS008. Fix, then promote.
4. Burn-down per rule, `adopt` then shrink: ~61BXXNJ (PM009, 438),
   ~339DX5F (PM007, PM003/PM005/PM008), ~ZX7DH32 (PATH001, 194),
   ~B755NCR (DOC006, DOC001, EXC005, MDL019, MDL005), ~ECWJCJ4 (DEAD001,
   COV001), ~ZYB1K0K (SYS001, 1296). Each rule's table carries its
   burn-down ticket (BASE002).
5. Heuristic families get `nature = Heuristic` and the message contract
   in the same step they become Errors; their findings are fixed or
   human-waived, not baselined unless the count is large (then both).
6. Last: delete `Warn`/`Advisory` and the ramp code once no rule or config
   uses them (the compiler enforces it).

**6.1.2a Implementation status (~7FDF275).** The store lives in
`gob-rules` (`baseline.rs`): `Baseline::parse`/`render` (canonical sorted
text; a conflict-marker file is a hard error), `adopt`, `prune`,
`partition` (muted vs live), `intersect_base` (a landing branch drops keys
the base already pruned), `growth` (BASE001) and `dead_tables` (BASE002),
plus `migrate_ratchet_lock`, which reads the old lock once (a top-level or
`pools`/`rules` map of rule id to keys), keeps its keys and refuses when a
baseline already exists. A brand-new table is the adopt event and is not
growth; BASE001 fails only added keys or a changed `ticket` on an existing
table. Both rules take a `BaselineHost` (head file, base-tip file, ticket
liveness). The `frob baseline` verbs, prune in `frob land`, the `baselined`
envelope section and the `frob migrate` hook are separate tickets.

**6.1.2b Product adoption (~BZF44PC).** `grimble check` and `crunk check`
read `frob-baseline.toml` at the repo root through `Baseline::load` (a
missing file is an empty baseline; a conflict-marker or unreadable file is
a config error) and apply it in their exception stage with `Baseline::mute`:
a decided Error whose reported fingerprint (rule, file path, message, the
key `refingerprint` assigns) is listed under its rule table is removed from
the findings and reported in `suppressed` with a `Baseline` exception
carrying the table's `reason` and `ticket`. Unresolved findings and
non-Errors are never muted, and tables of other products' rules never match.
Neither product has a ramp call left. `[grimble] strict` is a deprecated
no-op: still accepted, it logs a WARN and changes nothing (it also no longer
feeds the bind-cache digest). `[pm] strict` is the same: a deprecated
no-op in `frob-pm` (`apply_strict`) that logs a WARN and changes nothing,
because every PM rule is already an Error.

**6.1.8 Implementation tickets** (all under ~BA6CSGY): ~1G4B9C1 severity
enum collapse and config errors; ~7FDF275 `frob-baseline.toml` store with
adopt/prune/BASE001/BASE002 and the ratchet migration; ~MBFZHZD remove ramp-in
and `strictness`; ~RC646Y4 gate scopes and `release_severity` removal;
~291TPEB heuristic nature, message contract and agent/human rendering (the
reason-required waiver check is the existing EXC reason rule); ~BZF44PC
grimble and crunk adoption; ~XK1MB0D promote zero-finding and exact rules.

## 7. Profiles

v1's rapid/standard/fortress existed to dodge check latency. v2 has no
profiles: there is one `[land] verify` knob whose only milestone-1 value is
`"sync"` (`"ci"` is Milestone 2 or later (D36)), and no one-way ratchet.
`frob migrate` maps all three v1 profiles to `verify = "sync"`; standard and
fortress become identical, which is deliberate because v1's deferred
verification is not rebuilt. The `[check] strictness` knob is retired with
the ramp-in (6.1.3).

A rule's effective severity is its declared default, then an explicit
`[rules.<id>]` override, which always wins. Verbs that check at write time
(ticket fields, stories, exceptions) refuse only when the rule's effective
severity is Error and otherwise succeed with the finding as a warning in
the envelope.

The release gate is one more step after that: a rule may run only at
the release gate (`crunk check --gate release`, read by `frob release
status`). A rule declares it with the optional `gates = [release]` field
of `#[rule]` (`RuleDef::gates`); HUMAN001 and HUMAN002 do. At the local
and ci gates such a rule does not run and is reported as "not in this
gate"; `rule_in_gate` decides, with `[rules.<id>] gates` as the repo
override. The gate is chosen by `--gate local|ci|release`, defaulting to
`local`, or `ci` when `CI=true`.

Ramp-in is retired (6.1.3): a new rule ships at its declared severity, and
no step after the gate rewrites severities. `[rules] ramp` is still parsed
by `gob_rules::RuleSettings::from_toml` but ignored with a deprecation
warning. `frob release changelog` lists rules whose `since` is the release's
minor line (`gob_rules::shipped_in`) under "Newly live rules".

## 8. Crate layout for this layer

```
gob-rules              Rule trait, RuleMeta, Severity, Finding, Cx, waiver
                       matching, ratchet pools, inventory registry, family
                       namespaces per product
gob-macros             #[derive(Rule)], #[derive(Directive)], #[derive(Capability)],
                       #[derive(Command)], #[derive(ConfigTable)], #[derive(TicketSchema)]
gob-directives         PARSE DSL (emitted under the parsing product's namespace)
frob-obligations       DRIFT AFFECT COV TODO SCOPE PRE QUEUE TICK MILE
                       CROSSTICKET DEPR DOC DOCENUM NEGEXIST REF TEST TDD INV
                       REL VERSION REG DEC NARR POL(tickets, docs) and the
                       ticket-bound exits EXC003 EXC007 (milestone 1 also
                       emits EXC001 and EXC005 here; rules.md section 10.6;
                       TEST001 is owned by frob-tests, and COV003 is
                       registered as a never-emitted alias of it)
gob-rules              EXC family except the ticket-bound exits (Milestone 2);
                       exception matching (it lives in frob-obligations'
                       `apply_exceptions` today and ticket G06 moves it)
gob-check              the product-neutral check pipeline (grimble/grmb-spec.md 20.2)
frob-pm                PM family (pm-and-releases.md)
grimble-bind           SYS family (model drift) and BIND
grimble-capabilities   CAP family (CAP001, CAP002, CAP004; CAP003 retired; CAP005 in grimble-bind) and SYS012
grimble-lints          universal and language structural rules, NEAT, GPOL (code)
grimble-ci             CI and DK (grimble/rule-families.md)
grimble-arch           CYCLE ARCH LARGE DEAD DUP
grimble-security       SEC PII
grimble-vet            VET
frob-check / grimble-check   pipeline, selection, render; frob merges siblings
```

The split follows docs/design/shared/charter.md section 1: a rule that still makes
sense with no tickets, docs policy or release process is grimble. Each
rule crate compiles and tests alone (`cargo nextest -p grimble-arch`),
with a shared fixture harness in `gob-rules/testing`
that builds a snapshot from an in-memory repo. Markdown-driven cases
(`tests/mdtest/**/*.md`: a fenced repo, then expected findings) are the
primary test form, in the style of ty's mdtest; `insta` snapshots cover
rendering.

## 9. Open questions

- POL authoring: decided, section 3 (ast-grep-shaped declarative rules
  at grammar and U level, plus Rust; engine decided pending a spike).
- SARIF: in 2.0, scheduled after the findings model and text/JSON
  renderers exist and before the first public release (decided
  2026-10-02).

## 10. Exceptions: waivers, debt, quick fixes, and permanent decisions

Merged from the former rules.md.

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction 2026-10-02: v1 never had a
clean line between a waiver, debt, a quick fix that should expire
"somehow", and a permanent decision. Evidence: notes/v1/gates-and-rules.md
sections 10.15-10.16 (waive with until, follow_up, permanent, presets, debt,
deprecated, ratchet pools, rapid debt, twelve waiver hygiene rules, an
audit watermark), notes/v1/crunk.md FROBLEMS rows 7 and 15 (permanent
waivers impossible because WIRE002 demanded an open ticket, so anchor
tickets were kept open forever; self-citing follow_up blocked lands).

### 10.1 One primitive, four kinds, every kind has a machine-checkable exit

An exception suppresses one rule at one site. What differs is how it
ends. The kind is mandatory and determines the exit condition the tool
can evaluate without human judgement; there is no kind whose exit is
"someone remembers". Which findings each kind may park: an Unresolved
finding (universal-model.md 4.2) can be parked only by `defer` (with a
ticket) or `baseline`, never by `accept`, because accepting a loud
"could not examine" would silence the failure without supplying the
declaration that fixes it; an `accept` that names an Unresolved finding
is EXC016.

| Kind | Meaning | Exit condition (evaluated by the tool) | Must carry |
|---|---|---|---|
| `accept` | this rule does not apply here by design; permanent | never expires, but is re-validated: becomes STALE when a fresh full evaluation finds no matching finding, and REATTEST when the bound symbol's body digest differs from the attested digest the accept verb recorded as a lock entry in `frob.lock` (D45; the one REATTEST source) | `because` naming an ADR, a style anchor, or a one-sentence reason; for Error-severity rules a `review` event by a second identity or by an owner listed in `[exceptions] owners` (an audit trail, not an authorization control: the actor is a label, so a determined caller can set any label; real approval control is the host's review and branch protection) |
| `defer` | real debt, to be paid by a ticket | the named ticket reaches a terminal state (then the defer goes red until removed), or an optional earlier `until` date or metric target | an open ticket of type bug, task or chore; a reason |
| `hotfix` | a quick solution that must be revisited | hard expiry at `[exceptions] hotfix_days` (default 14), no extension; converting to `defer` requires a ticket; `land --hotfix` files the follow-up ticket itself | reason; the auto-filed ticket id |
| `baseline` | mass legacy findings admitted when a rule is introduced or tightened | a baselined key disappears when its finding disappears; the pool can only shrink; a key may be removed with a reason, never added after creation | the rule id, creation reason, and the pool file |

What is gone: `permanent="true"` (that is `accept`), `follow_up=`
(that is `defer`), `frob:debt` as a separate verb (it is `defer`),
presets (a preset was a way to avoid writing a reason; `accept
because=style#anchor` covers the legitimate cases), rapid-debt
(there is no deferred verification to owe), the anchor-ticket
workaround (nothing requires an open ticket to be permanent).

Evaluation boundary. An exit that names a ticket (`defer`, and the
auto-filed ticket of `hotfix`) is evaluated by frob only, because only
frob knows tickets (D28). grimble and crunk parse the exception, treat
`ticket=` as an opaque string and emit it in their `--json`; frob's
orchestrated check reads that JSON to decide EXPIRED and to enforce the
close guard. A standalone grimble or crunk reports such an exception as
UnresolvedExit (an exception state, not the Unresolved severity of
universal-model.md 4.1): parsed, valid, not evaluable here. Date-based and
digest-based exits are evaluated by each product itself. The budget per
component uses frob's component registry, so budgets are frob's too.

Milestone 1 (D36) implements `accept` and `defer` only, with EXC001,
EXC003, EXC005 and EXC007 (section 10.6 gives their meaning as built);
`hotfix`, `baseline`, budgets, the audit and `convert` are Milestone 2
or later (D36). A flagged exception still suppresses its finding; the
EXC finding is what fails the gate, with two exceptions. A `defer` whose
`until=YYYY-MM-DD` day (UTC, inclusive) has passed no longer suppresses and
raises EXC014; an `until` holding a `:` is a metric target that only the
product knowing the metric evaluates. An `accept` on an Unresolved finding
does not suppress it and raises EXC016. EXC017 reads the tool ids that a
`[[check.tool]]` `id_map` binds (a parser's built-in map is not read yet).

### 10.2 Syntax

Inline, one line, machine-read, exempt from the NARR narrative rules
(notes/research/documentation.md section 4):

```
# frob:accept COV006 because="docs/decisions/2026-10-02-dispatch-tables.md"
# grimble:defer ARCH001 ticket=01J9QKX3M8Z4T7N2V5B6C0D1E2 because="split after the parser lands"
# grimble:hotfix SEC002 because="rotate key, see incident ticket" ticket=01J9QMA7R2K5W8Y1H3F6G9P4S0
```

All four exception verbs spell the reason `because=` (the milestone-1
parser accepts only that spelling).

File- or package-scoped exceptions and anything longer than one line
live in `exceptions.toml` at the repo root (tracked), with one array
per product (`[[frob.exception]]`, `[[grimble.exception]]`,
`[[crunk.exception]]`; each product reads only its own), one table per
exception with the same fields plus `scope = "crates/x/**"`. The same
file holds only exception records; the attestation of every `accept`
(the attested body digest and time) is written by the accept verb as a
`symbol` entry in `frob.lock` (gob-lock, D45), and REATTEST compares the
live digest with it, so there is one source of truth for the digest. The
baseline pool is
`<product>-ratchet.lock.json` as before. grimble and crunk use the same
primitive through `gob-rules` with their own namespaces
(`grimble:accept`, `crunk:defer`).

frob also writes an `exception` event on the ticket a `defer` or
`hotfix` names, so the ticket page shows what is parked on it, and a
ticket cannot close while a `defer` still points at it (found through
the sibling `--json`) unless the land that closes it removes the defer
(the finding is fixed) or converts it.

### 10.3 Lifecycle and the single audit view

```
                 created
                    |
   accept --------- active ---- STALE (matches nothing)  -> removed by --fix
      |              |
      |          REATTEST (symbol body changed)          -> ack with reason or remove
   defer ---------- active ---- EXPIRED (ticket closed, date or metric met) -> error
   hotfix --------- active ---- EXPIRED (days elapsed)   -> error, convert or fix
   baseline ------- active ---- RETIRED (finding gone)   -> key dropped automatically
```

`frob exceptions` is the one verb: `list [--kind --stale --expiring
--by-rule --by-component]`, `audit` (a sampled review pass that records
verdicts STILL NEEDED, OBSOLETE, COP-OUT as events; the watermark idea
from v1 kept, but the sample is small and the verdicts are data),
`convert <id> --to defer --ticket ...`, `prune` (removes STALE and
RETIRED, is the `--fix` for EXC rules), `budget` (section 10.4).

STALE is decided only from a fresh full evaluation of that rule over
that file in the current run: never from a cached memo, never after an
`--only` run that skipped the rule, and never after a rule version bump
or a deleted `.frob/` (unknown is not stale). A site where the rule's
outcome in this run was Unresolved (an opaque subject, a `hole` such as
a parse error, a May edge) is not stale either: it is unprovable, so the
rule outcome must carry its Unresolved sites and neither EXC013 nor
`exceptions prune` may treat an accept there as matching nothing.
`exceptions prune`
performs that evaluation itself before removing anything. A baseline
key is a fingerprint (rule id, symref or file path, hash of the
normalized message), never a line number.

### 10.4 Budgets, so debt cannot quietly become the plan

| Control | Default | Effect when exceeded |
|---|---|---|
| `[exceptions] max_defers_per_component` | 25 | new `defer` in that component refused until one is paid or an owner raises the budget with a `budget-raise` event under the root `events/` |
| `[exceptions] max_defer_age_days` | 90 | EXC010 Warn at 60, Error at 90: the defer must be paid, converted to `accept` with review, or re-justified (a `review` event under `events/` that resets the clock at most once) |
| `[exceptions] hotfix_days` | 14 | hotfix EXPIRED, Error |
| `[exceptions] max_hotfixes_open` | 5 | `land --hotfix` refused |
| baseline pool growth | zero | a pool can never gain a key after creation; tightening a rule creates a new pool with its own reason |
| accept density | `max_accepts_per_rule_per_file` 3 | more than that is a sign the rule or the file is wrong; EXC011 Warn, the remedy suggests a style decision or a rule config change |

All `[exceptions]` knobs, including `owners`, `reattest_warn_days` and
`max_duplicate_reasons`, are materialized in the config file by `frob
init` (docs/design/shared/architecture.md section 1.6, which lists them); a missing one is
CFG001. Budgets and the audit are Milestone 2 or later (D36).

`frob status` prints the exception ledger beside the ticket queue:
counts by kind, age distribution, those expiring within a `--within <days>` window, and the trend
since the last release. The PM cycle report shows debt paid versus
added per cycle.

### 10.5 Reason quality (the cop-out problem)

Shared with ack reasons and waiver reasons in v1, now one checker in
`gob-rules`: minimum length, a boilerplate deny-list, no duplicate
reason text across more than `[exceptions] max_duplicate_reasons`
exceptions, and for `accept` on Error-severity rules the reason must
resolve to a document anchor or carry a `review` event. A reason that merely restates the rule name
("COV006 does not apply") is refused at write time.

### 10.6 Rules (family EXC, replacing the twelve v1 waiver rules, the three v1 debt rules, and parts of WIRE and REL001)

Milestone 1 ids, as implemented in `frob-obligations` (these four
numbers are authoritative; the design numbering that followed the
earlier draft is re-spelled below):

| Id | Fires when | Severity | Crate |
|---|---|---|---|
| EXC001 | exception with a bad reason (empty, boilerplate, restates the rule id, repeated words, under the minimum length) | Error | frob-obligations |
| EXC003 | `defer` names a ticket that has reached a terminal state | Error | frob-obligations (ticket-bound, frob only) |
| EXC005 | `accept` whose bound symbol body digest differs from the digest in `frob.lock` (REATTEST) | Warn | frob-obligations |
| EXC007 | `defer` names a ticket that does not exist | Error | frob-obligations (ticket-bound, frob only) |

Milestone 2 or later (D36), designed and not yet implemented:

| Id | Fires when | Crate |
|---|---|---|
| EXC002 | exception names a rule that can never match at this site (wrong scope) | gob-rules |
| EXC004 | `accept` REATTEST escalates to Error after `[exceptions] reattest_warn_days` | gob-rules |
| EXC006 | `hotfix` EXPIRED | gob-rules |
| EXC008 | exception on a rule declared `waivable = false` | gob-rules |
| EXC009 | over-broad scope (package exception on a rule that is not package-scoped) | gob-rules |
| EXC010 | defer older than the age budget | gob-rules |
| EXC011 | accept density exceeded | gob-rules |
| EXC012 | `accept` on an Error rule without a document anchor or review | gob-rules |
| EXC013 | exception is STALE (a fresh full evaluation finds no match; Warn, the fix is `prune`) | gob-rules |
| EXC014 | `defer` EXPIRED by date or metric target (`until=`) | frob-obligations (ticket-bound, frob only) |
| EXC015 | `defer` names a ticket not of an allowed type, or names itself | frob-obligations (ticket-bound, frob only) |
| EXC016 | `accept` names a rule at a site where the finding is Unresolved (park it with `defer` or `baseline`) | gob-rules |
| EXC017 | a native suppression (`#[allow(...)]`, `# zizmor: ignore[...]`, `// eslint-disable`) of a rule bound through a `[[check.tool]]` stage with no matching frob exception | gob-rules |

Severity defaults: EXC016 is Error and EXC017 is Warn; EXC005 is Warn in milestone 1; from Milestone 2 EXC004
is Warn for `[exceptions] reattest_warn_days` (default 14) then Error,
measured from the commit date of the change that made the digest differ
(found through the symbol history; nothing extra is stored); EXC013 is
Warn; everything else Error. Release (`frob release
stamp`) refuses while any EXPIRED exception exists; it does not refuse
on open `defer` (v1's REL001 refused on any debt, which pushed people
toward permanent waivers instead of honest defers).

### 10.7 Migration from v1

`frob migrate exceptions` rewrites: `frob:waive` with `follow_up=` or
`until=ticket-closed:` to `defer`; `frob:waive permanent="true"` to
`accept` with the reason, flagged for review if the rule is Error;
`frob:waive` with only a reason to `accept` when the reason resolves
or cites a doc, otherwise to `defer` against an auto-filed triage
ticket per component ("classify legacy waivers in X"); `frob:debt` to
`defer`; `until=<date>` to `hotfix` if within `[exceptions] hotfix_days` else
`defer`;
presets expanded to their text. The anchor tickets v1 kept open as
waiver targets are closed in the same migration once nothing points
at them.

## 11. Rule authoring: one rule, two files, compile errors first

Merged from the former rules.md.

Provenance: accepted, coordinator decision 2026-10-06. Owner requirements:
"the macros and code gen made so that it's impossible to mess up adding;
compile errors over runtime errors"; "for a single rule, the information
should live next to each other"; adding universal cross-language and
language-specific rules must be simple. Evidence and the full failure table:
notes/research/rule-authoring.md (82 rules mapped, 2026-10-06); background:
notes/research/codegen-macros.md.

### 11.1 What was wrong

One rule's information lived in up to eight places: a derive on a marker
struct, a check function in another module, hand wiring into a product's
groups, a string-keyed applicability table (`need_of`), product `applicable`
chains, a corpus elsewhere, a coverage allowlist and docs that silently
missed crunk's and grimble's rules (link-time `inventory`). `Tier::Lang`
named no language. A new frob rule cost 9 to 12 edits across 3 crates, and
nothing proved a registered rule was ever run.

### 11.2 The shape

A rule is two files side by side in the crate that owns its family:
`src/rules/<id>.rs` (declaration and evaluation) and `src/rules/<id>.md`
(the rule page, which is also its mdtest corpus, ty style). Rules may live in
several crates; everything about one rule lives in its two files, and shared
algorithms used by two or more rules are plain modules of the same crate.

```rust
#[rule(
    id = "COV001", slug = "untested-public-function",
    severity = Error, polarity = Pminus, must_measure = true,
    scope = Repo, fix = Manual,
    applies = universal(needs = [TestItems, Visibility], min_fidelity = F2),
    version = 1, since = "2.0.0",
)]
pub struct Cov001;

impl RepoRule for Cov001 { /* evaluation on the same type */ }
```

- Every field is required; only `min_fidelity` defaults (F1). A `host = TRAIT` field names the product host trait the evaluation is generic over, so the macro can probe `FileRule<dyn TRAIT>` and report a missing evaluation at the declaration (spike ~9R52NCF; host traits must be object-safe). The family is
  derived from the id; the product is positional (section 11.4).
- `applies` is `universal(needs, min_fidelity)`, `languages(L, ..; needs,
  min_fidelity)` or `project` (ledger, release, model, config). It maps 1:1
  onto GRL `lang *`, `lang [..]` and `lang -`; GRL's side-relation header is
  renamed `reads` so `needs` means capabilities everywhere, and GRL gains
  optional `since` and `fidelity` headers.
- Evaluation is a trait on the same type: `FileRule` or `RepoRule` (chosen by
  `scope`), `Measured` when `must_measure`, and a `stage(..)` body for rules a
  pipeline stage emits (tool parsers, the grimble model check).
- A `FileRule` may override `side_input(host, path, text)` (and `side_input_needs_text()` when it
  reads `text`) to name facts outside the file's own bytes, such as the state of link targets or
  ledger entries it cites. The text is hashed with the path into the findings cache key, so a
  change recomputes the file's findings; the default, empty, means the file text alone decides.
- `evidence` is required (or an Evidence section in the rule page): it
  names the lint-catalogue row and its E_det. A rule whose row is
  contested (C = 0.5) must declare `default = off`, and no new rule
  defaults to error before the precision ledger (N16) supports it
  (docs/design/shared/rules.md section 1). Warn and Advisory no longer exist (rules.md 6.1.1).
- `body = relay` (optional, `scope = Repo` only, not with `must_measure`) swaps `RepoRule` for
  `RelayRule`, whose `relay(host, files)` returns whole `Finding`s a sibling stage already
  computed. Unlike `Out`, that keeps the typed `UnresolvedReason`, per-finding severity, the
  required reason, custom anchors, byte ranges and fixes. Findings stamped with another rule's id
  are dropped (with a warning), and relay output is never cached: the stage owns its caching.
- Subjects are available for any repo rule: `RepoRule::examined` / `RelayRule::examined` return
  `Option<usize>` (`None` reports nothing), and `RuleSet::stage_counted(def, count)` does the same for a
  stage rule, so a `must_measure` stage rule with zero subjects is the required Unresolved.
  `RuleSet::stage_when(def, inapplicable)` gives a stage rule a product-fact `not_applicable`.
- Product-fact applicability is a method on the rule (`inapplicable`), whose
  reason is counted and printed.

### 11.3 One applicability resolver

`gob-caps`, a new leaf crate, holds `Lang` (a closed enum for built-ins,
including the pseudo-languages `opaque-text` and `binary`), `Fidelity`,
`Capability`, `Precision` and the const capability `MATRIX`; each adapter's
capabilities are a read of its row, so the languages page and rule
applicability cannot disagree. One pure function `resolve(applies, file
facts)` decides Examine, NotApplicable (declared by construction, never a
finding) or Unresolved (rolled up per rule and language) for every rule,
replacing `need_of`, `Tier`, product `applicable` chains and per-product
tables. Packs name languages as strings (packs-and-plugins.md 8).

### 11.4 Registration: generated lists, not link-time inventory

Each rule crate's `src/rules/mod.rs` is generated by `cargo dev gen
rules-index` (clippy `update_lints` and ruff `generate-all` style),
committed, GEN001-checked and checked by a crate freshness test (the generated `#[cfg(test)] mod tests`, so DEAD001 treats it as test code). A product
declares its rule crates in one hand-written line (`product_rules!`), and
the pipeline runs exactly that list, so a listed rule is run by
construction. Built-in Rust rules, GRL std rules and pack rules become one
runtime `RuleDef` (D76 parity). `build.rs` stays banned (security.md 2.8).

How it is built (~PBJ6GPZ). `gob_rules::indexgen` scans `src/rules/*.rs` for `#[rule(..)]`
files (the legacy derive is skipped) and renders `mod.rs`: one `pub mod` per file, `METAS`, an
`INDEX` (`RuleIndex`: crate name, the defs, `RENAMED` and `RETIRED` ids from an optional
hand-written `src/rules/retired.rs`), a const `assert_unique("crate", ..)`, `bind::<P>()` (a
`where Rule: FileRule<P>` bound per rule, so a host that lacks a rule's host trait fails to
compile) and the `rules_index_is_fresh` test. The text is laid out the way rustfmt leaves it, so
`cargo fmt --check` and GEN001 agree. `cargo dev gen rules-index` writes it for every crate (or
fixture) with a `src/rules` directory and `[package.metadata.gob] families` is enforced when
present. `gob_check::product_rules!` (`product`, `host`, `crates`) expands to `RULE_INDEXES`, the
product-level const check and `rules()`; `gob-dev` lists every product's `RULE_INDEXES` in
`products.rs` with the all-products check. Uniqueness is one namespace for ids, renamed ids and
retired ids and another for slugs; the panic text names both declarations. Product crates deny
`unused_crate_dependencies` (outside `cfg(test)`), so a rule crate dropped from the list while
still depended on fails `cargo check`. Until the migration tickets move rules over, each product
list is empty and the legacy inventory path is untouched.

The explicit product registry (~67J8R53). `gob_rules::PRODUCT_CRATES` lists, per product, the crates that declare its
rules; nothing is anchored at link time (`gob-dev` has no `link_inventories`, and the CLI roots are consumed through
`FrobProduct.cli` and `gob_dev::registry::verify_clis`). `gob_rules::check_registry` compares that list with the linked
`RuleIndex`es and names a listed crate that is missing from the build, an indexed crate that is not listed, and any duplicate
id or slug with both declaring modules. `gob_rules::Redirects` holds `RENAMED_IDS` and `RENAMED_SLUGS` (old name to current
name, followed through chains) so `Registry::by_id` and `by_slug` keep resolving old ids in config and directives, and
`RETIRED_IDS`, which stay reserved: a new rule reusing one fails, and no live id or slug may shadow a redirect. `gob-dev`
also scans `crates/*/src` for every `derive(Rule)` type and fails naming any that is not in its product's registry; `gen`
runs these checks before writing anything.

How the pipeline runs it (~GBBKJ6V). A product returns `Product::rule_set()`, a `RuleSet` built with `RuleSet::bind(rules(), host)`
from its `product_rules!` list (`host` maps the product and its snapshot to the host the rules were bound against) and
`RuleSet::stage(def)` for rules a pipeline stage already emits. `gob_check::run` then treats each `RuleDef` like a legacy
rule: file rules go through the one resolver per file (the same accounting pass as the legacy file checks, so fidelity rows stay
one per file), results are cached per file digest (file rules) or inputs digest (repo rules), `Out`/`Emitted` become
`Finding`s (`fire` located, `note` spanless, `unresolved` Unresolved), and a `must_measure` repo rule counts through
`Measured::subjects` while a file rule counts the files it examined; zero subjects is the required Unresolved. A rule's own
`inapplicable()` is asked once per pass, skips the rule (no finding, no zero-subject finding) and lands in the `fidelity.inapplicable`
map of the JSON report and as one `inapplicable RULE: reason` line of the text report. The legacy `file_checks`,
`repo_groups`, `applicable` and `includes` keep working beside it; the migration tickets delete them rule by rule.

### 11.5 Where each mistake is caught

Compile time: missing or malformed metadata; no evaluation; `must_measure`
without subject accounting; applicability not declared; an unknown language
or capability; a language-specific rule needing a capability its language's
adapter lacks; a universal rule no language can satisfy; duplicate id, slug
or renamed id within a crate, across a product's crates and across
products; a rule crate depended on but not listed; a missing `.md`, a
missing required section or a missing fire or clean example; a file stem
that is not the id; `since` not semver or in the future.

Gen time (GEN001), because rustc never sees an unreferenced file and
`build.rs` is banned: a rule file present but not indexed, and a rule in a
crate that does not own its family.

Test time, because they need the engine to run: that the examples produce
the outcome classes they state (rules.md), that the derived language
matrix cells hold, polarity conformance, and that a rule reads only the
capabilities it declares (moved into the types if undeclared reads appear).

### 11.6 Adding a rule

```
cargo dev new-rule COV007 untested-thing --universal --scope repo --needs TestItems,Visibility
cargo dev new-rule NEAT040 some-slug --lang rust,python --scope file --needs Imports
```

The scaffold writes the two files in the owning crate, regenerates the
index and runs the rule's own test; the generated rule builds and passes
unedited, and CI scaffolds into a temporary copy to prove it stays so. A
new rule in an existing crate is two hand-written files and nothing else;
a new rule crate adds one line to its product's `product_rules!`.

### 11.7 Migration

In tickets under the rule-authoring epic: a spike on one rule first, then
`gob-caps`, the resolver (behaviour-preserving), the attribute and `RuleDef`,
product lists, the pipeline over `RuleDef`s, per-crate migrations (frob,
grimble, crunk in parallel), the colocated `.md` as docs and corpus, docs
generation, the scaffold, plugin parity, the config consistency check and a
cleanup that deletes the derive, `Tier` and the rule `inventory`. Rules
written before the attribute lands use the old derive; afterwards only the
attribute.

### 11.8 Std rule codegen

`cargo dev gen std-rules` compiles each rule in `packs/std/rules/*.grl` to a Rust
module `packs/std/generated/<rule>.rs` (packs-and-plugins.md 6). There is no build script:
the modules are checked in and `cargo dev gen all --check` reports a stale or
missing one as GEN001.

Each module carries `#![forbid(unsafe_code)]`, and `design/model.grmb` gives the
`std_rules` node that owns `packs/std/generated/**` no grants, so any ambient effect
in a generated module is CAP001.

## 12. Testing a rule

Merged from the former rules.md.

Provenance: accepted, coordinator decision 2026-10-06 (owner: "make sure the
lints, mdtests, snapshots and so forth are designed with [the universal
model] in mind"). Evidence: notes/research/u-testing-audit.md (the audit
of D103 against U), notes/research/rule-testing.md (ruff, ty, clippy,
biome, oxc, rust-analyzer). Amends D103: ruff and ty test a two-valued
world (a case has diagnostics or not); U is not two-valued
(universal-model.md 4.1, 4.2), so the harness asserts U's outcomes, not
only the presence of findings.

### 12.1 Outcome classes

Every test case expects exactly one class, the vocabulary of grl-spec.md
section 12.9, shared by gob-mdtest, GRL examples and the grimble-bind corpus
(one example grammar for the whole project):

| Class | Meaning | What the runner checks |
|---|---|---|
| `fire` | the rule found what it looks for | the findings equal the markers |
| `clean` | the rule examined at least one subject and found nothing | zero findings of the rule at any severity, Unresolved included, and `subjects_examined >= 1` (or the stated `subjects=`), and the rule applied |
| `unresolved` | the rule could not decide | an Unresolved finding with the stated reason (`reason=`), required or not |
| `notapplicable` | the rule cannot apply to this artifact by construction | the rule reported NotApplicable with the stated reason, and no finding |

Modifiers `known-gap` (an Unresolved the project accepts, with a ticket)
and `fixed` (the case after applying the fix) come from grl-spec.md 9.

A clean result is certified, never inferred from silence: a rule that
examined nothing, did not apply, or was given a file no adapter reads does
not pass `clean`. This is universal-model.md 4.2 (subject accounting)
made executable.

The runner returns a `RuleReport` (rule, subjects total and examined,
not-applicable reason, findings) and every Unresolved finding carries a
typed reason (`Finding.reason`), never a reason parsed from message text.

### 12.2 Markers and strictness

Markers name the severity or class: `error:`, `warn:`, `advisory:`,
`unresolved[REASON]:` (optionally `required`), with optional column and
message text. A finding with no span (a rolled-up Unresolved, a repo-scope
finding) is asserted by a header expectation on the case.

Strict mode (ty's "unexpected error") counts every class: an Unresolved
or Advisory finding of a selected rule that no marker matches fails the
case, so a corpus author can never silence honesty to make a test pass.

### 12.3 Required cases per rule

Derived from `RuleMeta` (polarity, tier, `must_measure`, `needs`) and
checked by the coverage meta-test, with a shrink-only allowlist keyed by
(product, rule, case kind), each entry naming a ticket:

| Rule property | Required cases |
|---|---|
| every rule | `fire`; `clean` over at least one subject |
| polarity P+ | `unresolved`: the offender is reachable only through a May edge or sits in an opaque region |
| polarity P- | `unresolved`: the good thing is present only on a May edge, or the needed answer is Unknown |
| polarity P0 | `unresolved`: one side is not Exact |
| polarity Pn | `unresolved`: the count is only bounded (lo <= N < hi) |
| polarity Pc | `unresolved`: the path runs only through May edges; the poisoned frontier is named |
| `must_measure` | `unresolved reason=vacuous required`: zero subjects is Unresolved, never clean |
| tier Universal | the language matrix of section 12.4 |
| lexical rule (`needs = Lexical`: text, literals, prose only) | `opaque_fire`: an `expect=fire cell=island` block, a `fire` inside an opaque region, beside an `unresolved` structural rule over the same region |

Each rule's fire and clean cases live in one suite file.

### 12.4 The language matrix for universal rules

A universal rule is tested in every fidelity class, not only in the
language it was written for: Rust (F3), Python (F2), TypeScript (F2), C#
(F1), markdown (F4), a text file with no adapter (F0), a binary file and
an embedded opaque island. The expected class of each cell is derived
from the rule's `needs` and the adapter's capability cells; a written
expectation that disagrees with the derived one fails, so the matrix
cannot be satisfied by copying. Parity cases render one logical shape in
three languages with one expectation.

The harness is `gob_mdtest::matrix` (blocks carry `cell=` and `parity=`); gaps are
`[[matrix_gap]]` entries in `crates/gob-mdtest/coverage-allowlist.toml`, each with a
ticket, and the list may only shrink.

An artifact with no adapter yet is `unresolved` with reason `fidelity`
for capability rules, rolled up to one finding per rule and language
(universal-model.md 3.3, 6: the worst case is F0 with everything
Unresolved). `notapplicable` is reserved for binary artifacts and for
languages that lack the feature by construction (a declared
NotApplicable capability cell).

### 12.5 Fidelity is measured, not claimed

An adapter's fidelity level is derived from its conformance corpus
(universal-model.md 3.3: F1 units and containment, F2 Must lexical edges,
F3 apply edges with declared status, F4 attributes, bound comments,
regions and phases); the test fails when the declared level differs from
the measured one in either direction. Every adapter ships a capability
matrix snapshot, a garbage-input case (no panic; Unresolved or
NotApplicable) and a partial-parse case. `frob doctor --languages`, the
languages page and the README table are generated from the same data.

### 12.6 Fixes and snapshots

The fix invariants run for every case with a fixable finding (ruff's
harness): a fixpoint within 10 rounds, a reparse after each round with
parse status and opaque or hole counts never degrading, no fixable finding
left, and no finding changing class from `fire` to `unresolved` (a fix
that hides code inside a macro or an opaque region fails).

Snapshots render the outcome class, the Unresolved reason in words and its
remedy, and the fix diff with its tier. The snapshot update mode never
changes a case's outcome class silently; a class change needs an explicit
second switch.

### 12.7 Polarity conformance and the ecosystem layer

A standard small repository per polarity (a May-only edge, a Must edge,
an opaque region, an Unknown visibility) is run against every shipped
rule, so "the rule behaves as its declared polarity says" is a test, not a
claim (universal-model.md 4.5, Theorem 3: never an Error or Warn whose
premise is false). The frob corpus is
`crates/frob-obligations/tests/polarity_conformance.rs`: it evaluates every
shipped rule over the four repositories and fails when any P- rule emits a
certain `Error` on a May-only, opaque or Unknown-visibility absence; a
forged-finding control proves the oracle can fail. The ecosystem check (build-test-ci.md 6) reports files
and subjects examined per rule and language, and a drop in subjects
examined is a regression even when the finding count falls.

### 12.8 Incompleteness: the oracle column (grimble/rule-families.md 2.3)

Honesty keeps frob from a false answer, not from answering Unknown too often,
so a corpus case also carries the true answer, known by construction. A case
(`gob_check::incompleteness`) names a language, a capability, the `oracle`
answer (`yes`, `no`, or `unknown` when genuinely undecidable) and the
`observed` answer. Per language and capability the harness reports the
false-Unknown rate: cases answered Unknown while the oracle is decided, over
all cases whose oracle is decided (undecidable oracles are not counted).

The gate compares that rate with a committed baseline
(`crates/gob-check/tests/fixtures/incompleteness/baseline.toml`):

- a rate above the baseline's fails like a regression; a lower rate passes and
  the baseline is then refreshed with `Report::to_baseline_toml`;
- a cell with no baseline is held to zero; a baselined cell that no longer has
  a decidable case fails as unmeasured (the same rule as a drop in subjects
  examined, section 12.7);
- a false Must (a decided answer that differs from the oracle, or a decided
  answer to an undecidable question) fails always and is never baselined.

Each case also carries a probe (`file`, `query`, `source`) that the real
adapter reads (`gob_check::incompleteness_live`): `visibility` is the symbol's
declared visibility, `imports` is whether the complete parse lists the target,
`resolve_ref` is Yes only for a proven (Must) call edge, and a capability the
language's adapter does not provide is Unknown. The test `oracle_live` fails
when the committed `observed` column differs from these live answers (a source
that no adapter parses is an error, not a verdict, so a flaky parse never
flips the column). Regenerate the column deliberately with
`FROB_BLESS_ORACLE=1 cargo test -p gob-check --test oracle_live`, then review
the diff and refresh `baseline.toml` by hand if a rate moved.

### 12.9 Native coverage providers

Native coverage is one shared pipeline with one per-language seam. Sections
9.1 to 9.4 describe the contract, the registry, the flag and the threshold knob;
9.5 lists the shipped languages. The source of truth is the module docs of
`frob_evidence::coverage` (`crates/frob-evidence/src/coverage/mod.rs`).

#### 12.9.1 The CoverageProvider contract

A language takes part by implementing `coverage::CoverageProvider` (`Send + Sync`)
on a unit struct in its own module under `coverage/`. The trait has six methods:

| Method | Returns | Purpose |
|---|---|---|
| `provider()` | `Provider` | the test provider whose `--coverage` run this measures |
| `language()` | `&'static str` | recorded on the summary and used for `.frob/coverage/<language>.info` |
| `required_tool()` | `&'static str` | the executable that must be on `PATH` |
| `has_tests(root)` | `bool` | whether the repository has tests in this language, so a report is owed |
| `plan(ws, reference, out_dir)` | `Result<CoveragePlan, CoverageError>` | the command to run and where its raw report lands |
| `to_lcov(ws, plan)` | `Result<String, CoverageError>` | converts the raw report to lcov text |

`CoveragePlan` holds `program`, `args`, `cwd`, `env` (added on top of the
plain-text defaults) and `report` (the raw report path, in any format `to_lcov`
reads). Paths in the lcov text may be absolute; the shared normaliser fixes them.

Everything else is shared and is not the provider's business: finding the tool,
running the command through the allowlisted `gob_exec::Runner` with the
workspace timeout, normalising paths to repo-relative form, writing
`.frob/coverage/<language>.info`, merging every language's file into the
`[coverage] report`, and recording a `CoverageSummary` on the evidence record.

The outcome is one of three `CoverageStatus` values:

- `NotRun`: the tool is not on `PATH`, the command could not be started, or the
  output directory could not be created. Never a failure.
- `MissingReport`: `plan` failed (other than a missing tool), the command timed
  out, or `to_lcov` found no report or an unreadable one. A failed write or merge
  is also `MissingReport`.
- `Measured`: the per-language file and the merged report were written; the
  summary carries lines and branches hit and found, and a digest.

A command that exits non-zero but does not time out is not failed by itself; the
report decides the outcome.

#### 12.9.2 The PROVIDERS registry

`PROVIDERS` (`&[&dyn CoverageProvider]`, in `coverage/mod.rs`) is the only list of
languages. Its entries, in order, are `rust::RustCoverage` (nextest),
`python::PythonCoverage` (pytest), `js::VitestCoverage` (vitest),
`js::JestCoverage` (jest) and `csharp::CsharpCoverage` (dotnet). `registered(provider)`
returns the entry whose `provider()` matches. A test provider with no entry,
such as `unity`, is recorded `NotRun` with the reason "no coverage provider is
registered for <provider>". COV004 reads the same registry. Adding a language is
one new module under `coverage/` and one `PROVIDERS` entry.

#### 12.9.3 The --coverage flag

`frob ticket evidence add <ticket> --provider <p> --ref <filter> --coverage` runs
the tests first and then the provider's coverage command, and records the
per-language summary on the evidence record. A coverage failure never fails the
capture. The flag belongs to test-runner providers only: `file`, `attestation`
and `command` are rejected with a usage error. `unity` is accepted but has no
registered provider, so it records `NotRun`. `frob test` has no `--coverage`
flag; coverage is captured only through `ticket evidence add`.

#### 12.9.4 The [coverage] require_reports knob

`[coverage] require_reports` (boolean, default `true`, enforcement) is read by
COV004 in `frob-obligations`. When it is true, each registered provider whose
language `has_tests` and has no `.frob/coverage/<language>.info` yields one COV004
finding: an Unresolved "not run" finding when the tool is not installed, otherwise
a "has tests but no coverage report" finding. When it is false, neither finding is
produced, and the `threshold` checks still run. The check looks at the
per-language file, not at the evidence record's status. The file COV004 reads is
`[coverage] report` (default `lcov.info`). Key reference:
[config](../../reference/config/frob.md).

#### 12.9.5 Per-language providers

Rust is
`coverage::rust::RustCoverage`: it runs
`cargo llvm-cov nextest [--profile <p>] --lcov --output-path <raw> <filter args>`
at the repository root, the shared normaliser rewrites the lcov to
repo-relative paths into `.frob/coverage/rust.info`, and every language file
is merged into the `[coverage] report` that COV004 reads. A missing
`cargo-llvm-cov` is recorded as not run, never as a pass; a run that leaves no
report is a missing report, which COV004 flags when `[coverage] require_reports`
is true and the repository has Rust tests.

Python is `coverage::python::PythonCoverage` under the `pytest` provider: it runs
the same pytest launcher the provider uses (`[tests] python`, else the repository
`.venv`, else `pytest`) with
`--cov --cov-report=lcov:<raw> <pytest args>` at the repository root (needs
`pytest-cov`, which brings `coverage`). The lcov goes through the same normaliser
into `.frob/coverage/python.info` and the merged report. A missing `coverage`
executable is recorded as not run, never as a pass; a run that leaves no report is
a missing report, which COV004 flags when `[coverage] require_reports` is true and
the repository has `test_*.py` or `*_test.py` files.

JavaScript and TypeScript are `coverage::js::VitestCoverage` and
`coverage::js::JestCoverage` under the `vitest` and `jest` providers; both record the
language `javascript` (TypeScript sources included) into
`.frob/coverage/javascript.info`. The project's own runner (`node_modules/.bin`, else
`PATH`) runs at the repository root: vitest as
`vitest run --coverage.enabled --coverage.provider=<v8|istanbul> --coverage.reporter=lcov --coverage.reportsDirectory=<raw>`
(v8 is the c8 lineage; the backend is whichever of `@vitest/coverage-v8` or
`@vitest/coverage-istanbul` is installed, v8 first), jest as
`jest --ci --coverage --coverageReporters=lcov --coverageDirectory=<raw>` (jest's bundled
istanbul). Records under `node_modules` are dropped before the shared normaliser
rebases paths. A missing `node`, runner, or vitest coverage package is recorded as
not run, never as a pass; a run that leaves no (or an empty) report is a missing
report. COV004 owes a report only when a `*.test.*`, `*.spec.*` or `__tests__` file
exists and the root `package.json`, a workspace member's `package.json` (npm/yarn `workspaces`,
pnpm `pnpm-workspace.yaml`; literal paths, `dir/*` and `dir/**`), or a `<runner>.config.*` file names the runner;
a repository naming both is claimed by vitest alone.

C# is `coverage::csharp::CsharpCoverage` under the `dotnet` provider, recording the
language `csharp` into `.frob/coverage/csharp.info`. It runs
`dotnet test <projects> <flags> --nologo --collect:"XPlat Code Coverage" --results-directory <raw> [--filter <ids>] -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=lcov`
at the repository root, taking the same project paths, `--no-build`, `--no-restore`,
`-c <config>` and test ids the dotnet evidence provider accepts. Coverlet nests its
`coverage.info` in a per-run directory under `<raw>`; the provider finds it, drops records
under `bin`/`obj`, and the shared normaliser rebases paths. A missing `dotnet`, or no
project/props file naming `coverlet.collector`, is recorded as not run, never as a pass;
a run that leaves no (or an empty) report is a missing report. COV004 owes a report when
a `.cs` file outside build output declares an xUnit, NUnit or MSTest test. Unity editor
coverage is not part of this provider.

### 12.10 Tests and CI modelled on ruff and ty

Owner request 2026-10-06: build the tests, snapshots and CI/CD like
Astral's ruff and ty. Most of docs/design/shared/build-test-ci.md section 2 already follows them (mdtest is
ty's format, insta snapshots, rule docs as tests). The rest:

| Practice (Astral source) | Ours |
|---|---|
| Rule tests as markdown with inline assertions; `<!-- snapshot-diagnostics -->` snapshots the rendered diagnostics of a section (ty mdtest) | `gob-mdtest` already has markers and positive controls; it gains the `snapshot-diagnostics` header, which writes an insta snapshot of the full text rendering (source excerpt, labels, help) for that file |
| One fixture file per rule plus a snapshot of its diagnostics, and a registry test that no rule lacks one (ruff `resources/test/fixtures/<linter>/<CODE>.py`) | `crates/<product>-rules/resources/test/fixtures/<FAMILY>/<RULE>.<ext>` for larger real-shaped inputs; a registry-driven test fails naming every registered rule with neither an mdtest fire/clean pair nor a fixture |
| Fix snapshots and fix convergence: apply fixes to a fixpoint, snapshot the diff, fail if a fix introduces a parse error or does not converge (ruff test harness) | the gob-fix harness (~29MKDDF) snapshots each fixable rule's diff and runs the fixpoint (at most 10 rounds), reparse and no-new-error checks for every fixture |
| Inline parser tests: `test_ok`/`test_err` comments in parser source extracted to `resources/inline/{ok,err}` with AST and error snapshots (ruff_python_parser, from rust-analyzer) | Implemented (T-2GG2KXR). GRL, .grmb, directives and the crunk.toml spec parser use `// test_ok NAME` / `// test_err NAME` blocks (plain `//` comments; names are `[a-z0-9_]+`; at least five of each per parser). `cargo dev gen inline` (part of `gen all`) writes each block to `crates/<crate>/resources/inline/{ok,err}/NAME.<ext>`; a stale or orphaned extraction fails `cargo dev gen --check` (GEN001). Each crate's `tests/inline.rs` parses every file, asserts ok cases are clean and err cases report errors, and insta-snapshots the tree and errors. `frob\:` and `grimble\:` in a block extract as `frob:` and `grimble:` so directive fixtures are not live directives in the source |
| Formatter idempotence and stability (ruff_python_formatter) | `grimble fmt` and the GRL printer: format(format(x)) = format(x) and parse(print(t)) = t over every fixture and a proptest generator |
| Snapshot hygiene: no stale or unreviewed snapshots (`cargo insta test --unreferenced reject`) | the nextest step runs with `INSTA_UPDATE=no`; a `snapshots` step in `cargo dev ci` fails on unreferenced or pending `.snap.new` files |
| Ecosystem check: run the base and PR binaries over pinned real projects and comment the finding diff (ruff ecosystem, ty ecosystem-analyzer) | `cargo dev ecosystem`: a pinned corpus (`ecosystem.toml`, repository and SHA per entry: Rust, Python, TS/React, C#/Unity, this repo) checked by both binaries; report = per-rule added/removed/changed findings, crashes, Unresolved deltas and timing; non-blocking PR comment; runs on goway helpers. Implemented (~9HS3VP7): see "Ecosystem check" below |
| Fuzzing in CI (ruff `fuzz/`, built on every PR) | `fuzz/` with cargo-fuzz targets for every parser (GRL, .grmb, directives, crunk.toml, ledger events) and the fold; PRs build the targets and run each 60 s; the nightly job (`.github/workflows/fuzz-nightly.yml`, every action pinned by SHA) runs the same `fuzz-build` step with `FROB_FUZZ_SECONDS=480`, uploads the reproducers and files one issue per crash. Implemented: `fuzz/` (targets `grl`, `grmb`, `directives`, `crunk_toml`, `ledger`), the `cargo dev ci --step fuzz-build` step (Linux, nightly toolchain, `cargo-fuzz` 0.12.0) |
| Deterministic benchmarks on PRs (ruff on CodSpeed) | instruction-count benchmarks (gungraun, the maintained successor of iai-callgrind, Valgrind based, no external service) compared against the base and commented (implemented for the plan executor and the Rust parser: `crates/gob-plan/benches/ic_plan.rs`, `cargo dev bench-ic`; cold and warm check are still to add); criterion stays for the scheduled wall-clock bench |
| Change detection: skip jobs a diff cannot affect (ruff `determine_changes`) | a first `changes` job maps paths to job sets (Rust, docs only, crunk node and playwright ~2H41VF1, workflows); a docs-only PR runs fmt, gen check and frob check only (implemented: `crates/gob-dev/changes.toml`, `cargo dev changes`) |
| Hygiene jobs: cargo-shear, cargo-deny, typos, MSRV | `deny` (cargo-deny advisories, licenses, bans), `shear` (unused deps), `typos`, `msrv` (build at `rust-version`) steps in `cargo dev ci`, each a tool pinned in frob.toml like zizmor |
| Release through one workflow with wheels and binaries (cargo-dist plus maturin) | unchanged: the hand-written release.yml (D83) already does both |

#### Fix harness (~G4WAFJT)

`gob_fix::run_fixture` is the engine-agnostic fix harness. The caller passes
an `observe` closure (parse and check the current files, return an
`Observation`: per-file `ParseStatus`, opaque and hole counts, findings with
class fire or unresolved, and the proposed fixes). Each round plans the fixes
at the given tier, applies them in memory (multi-file fixtures, overlap
losers retried next round) and re-observes, for at most `MAX_ROUNDS` (10)
rounds. A fixture fails with a `Violation` when a round degrades a file's
parse status (a new parse error), grows the opaque or hole count (so a fix
that wraps code in a macro fails even when the finding vanishes), turns a
finding that fired into an unresolved one (same fingerprint), applies an
out-of-range edit, never reaches a fixpoint (oscillation), or leaves a
fixable finding after the fixpoint. `Outcome::snapshot_text` is the round
count plus the unified diff original to final, snapshotted with insta.
`missing_fixtures` names fixable rules with no fixture; with no fixable rules
it passes vacuously. Self-tests in `crates/gob-fix/tests/harness.rs` cover
the oscillating, parse-breaking, macro-wrapping, hole-growing, no-op and
overlapping cases. Per-rule snapshots for the real fixable rules are wired in
the rule crates (follow-up tickets under the parent epic).

Every row is a `cargo dev ci` step or a nextest test, so local runs, goway
runs and GitHub Actions run the same thing (docs/design/shared/build-test-ci.md section 4).

#### Ecosystem check (~9HS3VP7)

`ecosystem.toml` pins six real projects by commit (frob, ripgrep, click,
zod, shadcn-ui, UniTask: Rust, Python, TypeScript/React, C#/Unity); an entry
may restrict `tools`, otherwise `frob check`, `grimble check` and `crunk
check` all run. `cargo dev ecosystem --base-bin DIR --head-bin DIR` fetches
each project shallowly at its commit into `target/ecosystem/<name>` (reused
when already on that commit), cleans untracked and ignored files before every
run so one binary's caches never reach the other, alternates which build runs
first, and prints a markdown report. Run it on a helper with
`goway run -- cargo dev ecosystem --base-bin ... --head-bin ...`.

Matching: a finding is `(rule, file, message)`, never its line, so shifted
code is not a change; duplicates count as a multiset and ordering is sorted,
so output order is irrelevant. Same key with another severity is `changed`; the
same rule and message in another file is `changed` (a rename). An empty base
makes every head finding `added`. Per rule the report gives added, removed,
changed and the Unresolved delta, plus base and head wall time per tool.

Failure handling: a signal, a timeout, a missing binary, or an exit without a
JSON envelope is a crash. A head crash is listed first and named in a
`Head crashes` block, never folded into a count. A base that fails gives no
diff (the head count is shown alone); both sides returning the same
structured error (crunk without a `crunk.toml`) collapses to "not applicable";
any other pair of failures is shown with both causes. A project that cannot be
fetched is reported and the corpus continues.

CI: `.github/workflows/ecosystem-pr.yml` builds both sides in release, runs the
command, writes the job summary and creates or edits one comment found by its
`<!-- frob-ecosystem -->` marker (it does not use `--edit-last`, which would
overwrite another job's comment). The job and the comment step are
`continue-on-error`, and the command exits 0 for findings and crashes, so the
report never fails a PR; a fork's read-only token only loses the comment, the
summary remains. Comments are truncated below GitHub's 65536 character limit.

## 13. Tool binding: bind before own

Merged from the former rules.md.
Status of this chapter: draft.

Provenance: accepted direction, owner question 2026-10-08: "I want to be sure
that we aren't retreading the work of things like ty and ruff ... can we
use what's already been built and pipe it through our thing?" Evidence:
notes/research/lint-reuse-research-2026-10-08.md (108 fetched sources;
aggregators qlty, Trunk, MegaLinter, reviewdog, pre-commit, rules_lint,
Sonar, Semgrep; crate publication and stability facts from crates.io and
the projects' own repositories) and the evidence-weighted catalogue
notes/research/lint-catalogue-2026-10-08.md. Extends docs/design/shared/rules.md section 4
(tool stages); epic ~224NQP4.

### 13.1 The boundary

frob, grimble and crunk never reimplement a single-language rule that a
maintained community tool already ships. They own only what no such tool
does: universal rules over U, architectural and cross-file rules,
cross-language rules, design-system rules, and everything tied to
tickets, evidence, leases and releases.

For a bound tool:

- It runs as a pinned subprocess through gob-exec, never as a linked
  library. A process boundary is the only interface these projects
  promise to keep: ruff's crates are published as "internal component
  crate" with no semver guarantee, ty is 0.0.x with breaking changes
  allowed between any two releases, oxlint's and Biome's linter crates
  are not published at all, clippy needs a pinned nightly with rustc-dev
  (research section 2).
- The project's own configuration is read, never rewritten: the user's
  editor, pre-commit and CI see the same findings frob does.
- Output is SARIF 2.1.0 where the tool emits it (oxlint, Biome,
  golangci-lint, Roslyn, ESLint through a formatter), else the tool's
  native JSON (ruff, ty, pyright, mypy, cargo `--message-format=json`).
  Each finding keeps the tool's id as `source_rule` beside the mapped
  frob id; frob applies baselines, ratchets, exceptions, severity,
  ticket scope and the land gate itself.
- The tool owns its fixes and its suppression comments. frob runs the
  tool's fix inside the ticket scope (tier A) instead of reimplementing
  it, and EXC017 reports a native suppression of a bound rule that has
  no frob exception.
- A tool that did not run, failed its version probe, exited with an
  undeclared status or produced unreadable output is TOOL001 Unresolved
  (rules.md 4), never a silent pass.
- Duplicate findings from two tools (or a tool and a native rule) on the
  same location and normalised id are merged; the id map declares the
  equivalences.

What frob adds over running the tools directly is the product: one
report and one gate across every tool and language, hold-the-line
baselines, exceptions with owners and expiry, ticket-scoped checks,
evidence and land gating, and loud failure when a tool silently did not
run.

### 13.2 Tool definitions are data

Following qlty's `plugin.toml` and Trunk's `plugin.yaml`, each bindable
tool is a data definition shipped in the std pack (packs-and-plugins.md), not code:

- pinned known-good version and a version probe;
- command variants keyed by version range (tools rename flags; Trunk
  carries ruff's renames this way);
- output format and parser id (sarif, cargo-json, ruff-json, ...);
- exit-code classes: success, findings, tool error;
- config files that affect results (part of the cache key) and the
  native suppression pattern (for EXC017);
- the id map to frob ids and equivalences for dedup;
- fix command, if any, and whether it is safe to run unattended.

Results are cached by (file digest, tool version, config digest). Tools
are found on the project's own path first (`uv run ruff`, the repo's
`node_modules/.bin`, the pinned toolchain); a hermetic download of the
pinned version is a later option behind gob-trust (security.md), never
implicit.

uv projects get their environment in two places. `frob work` runs
`uv sync --frozen` (`uv sync` without a `uv.lock`) in each new worktree
when the primary checkout has a `.venv`, pinning `UV_PROJECT_ENVIRONMENT`
to the worktree's own `.venv` so the worktree imports its own code; it
tries `--offline` first and is best effort (a failure is logged and the
worktree is still created). A check stage that runs `uv run` in a
checkout with no `.venv` syncs first, or reports Unresolved with the
remedy when the sync fails (see `docs/reference/tool-stages.md`, uv-run
stages). The check-side sync is skipped when `UV_PROJECT_ENVIRONMENT`
is already set in the check run's environment; `frob work` does not
skip on it, it pins its own value.

### 13.3 Per ecosystem

| Ecosystem | Default binding | Notes |
|---|---|---|
| Rust | rustc and clippy through `cargo --message-format=json` | clippy only as a driver; formatters through FMT001 |
| Python | ruff (native JSON); ty or pyright for types | ty check for diagnostics; types per site through `ty server` (section 13.4) |
| JS/TS | oxlint (SARIF), type-aware rules opt-in | covers ESLint core, react-hooks, jsx-a11y and 59 of 61 typescript-eslint rules through tsgolint; native Windows binaries; `@oxlint/migrate` reads ESLint flat configs. ESLint stays bindable for ESLint-only plugins; Biome when a repository already uses it. Type-aware lint is outside oxlint's semver promise, hence opt-in |
| CSS | stylelint | |
| C# and Unity | Roslyn analyzers through SARIF error logs, incl. Microsoft.Unity.Analyzers and their suppressors | the unity pack (code-model.md) owns only what they do not cover |
| Go | golangci-lint (SARIF) | |
| any | typos (SPELL001), formatters in check mode (FMT001), semver checkers (VERSION001) | |

### 13.4 Language facts for universal rules are different

Universal and architectural rules need facts (symbols, scopes, calls,
types) inside gob's model, not findings. The boundary there is:

- Parsing stays in gob (tree-sitter and ast-grep-core, D42, D96).
  oxc_parser and oxc_semantic are the only plausible in-process
  replacements for JS/TS and are reconsidered only if tree-sitter's
  scope facts prove insufficient by measurement.
- Type facts (D119) come from the language's checker over a pinned
  protocol, failing closed to Unresolved on any version change: Python
  through `ty server` (LSP hover and inlay hints), with `dmypy inspect`
  for repositories on mypy; TypeScript through a small Node helper on
  `@typescript/typescript6` (`getTypeAtLocation`), since TypeScript 7
  shipped without an API. A spike measures latency on 1000 sites before
  either is adopted.

### 13.5 Consequences

- Native rule tickets for single-language checks that a bound tool
  already ships are re-scoped to a binding plus an id map, or dropped
  with a reason.
- The SARIF parser (~WAZA1EH) and the tool-definition format come first;
  every binding depends on them.
- The web profile defaults to oxlint, not ESLint (~V4KM7K8 re-scoped).

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D3

Rules, directives, capabilities, commands, config tables declared once via derives; docs and schemas generated

### D32

Rule identity (audit M3, M4, M5): EXC replaces WAIVE and DEBT everywhere; one family-to-crate table in boundaries.md covers every family; ids are FAMILYNNN with an optional slug alias in all products; grimble policy rules use `GPOL`; PARSE and DSL live in gob-directives and are emitted under the parsing product's namespace; policy files live next to the owning product's config

### D88

Owner decision 2026-10-04: the v1 web-app lint families (WEBSEC, A11Y, SQL, SEO, COMPLY, WEBPERF, LAUNCH, ROUTE; 249 v1 ids) and the STORE/SYSDESIGN/GRAMMAR system-design family (102 v1 backlog tickets) move to crunk as rule packs on the public pack mechanism, not frob or grimble core; their v1 requirement-bearing tickets are imported under crunk

### D89

Owner review 2026-10-04, refines D88 by the charter.md boundary (grimble: systems and code in any language; crunk: the rendered front end): crunk takes A11Y, SEO, LAUNCH and WEBPERF's markup and asset rules (pack crunk-web); grimble takes WEBSEC (into SEC), SQL, COMPLY (with PII), ROUTE, WEBPERF's server rules (pack grimble-websec) and STORE/SYSDESIGN/GRAMMAR (pack grimble-sysdesign); v1 tickets import under the matching area

### D21

Exceptions are one primitive with four kinds (accept, defer, hotfix, baseline) whose exits the tool evaluates; budgets and one reason checker

### D28

Boundaries (audit H6, H7, M14, M17): ticket-bound exception exits and the close guard are evaluated by frob only, from sibling `--json` in which `ticket=` is opaque; standalone grimble and crunk report such exceptions as Unresolved; lock and ack mechanics move to `gob-lock` with one lock file per product (`frob.lock`, `grimble.lock`) and an `ack` verb per product; `.grmb` `waive` becomes the four exception kinds; frob consumes grimble entities and `binds` edges only through `grimble --json`; PM026 uses the gob-symbols public-API graph only

### D45

Exceptions (T-0022): milestone-1 ids are EXC001 bad reason (Error), EXC003 defer ticket terminal (Error), EXC005 accept body digest differs from `frob.lock` (Warn), EXC007 defer ticket missing (Error); flagged exceptions still suppress and the EXC finding fails the gate; `until=` is not evaluated; the other EXC ids are renumbered and marked Milestone 2

### D107

Owner requirements 2026-10-06 ("impossible to mess up adding; compile errors over runtime errors"; one rule's information side by side): a rule is two colocated files (`src/rules/<id>.rs` with a `#[rule]` attribute whose fields are all required and an `applies = universal | languages | project` declaration, and `<id>.md`, its page and mdtest corpus); one applicability resolver over a const capability matrix in a new leaf crate gob-caps (closed `Lang` enum for built-ins); evaluation on the same type (`FileRule`, `RepoRule`, `stage`); registration by generated per-crate indexes and one `product_rules!` line per crate, with const uniqueness, replacing link-time inventory for rules; a `cargo dev new-rule --universal|--lang` scaffold. GRL renames its side-relation header to `reads` and gains `since` and `fidelity`. Also: SYS013 (undeclared coupling) accepts a code edge between two owners when any flow connects them in either direction; a flow's direction is data movement (grimble/grmb-spec.md 4.2)

Also logged against: notes/research/rule-authoring.md.

### D106

Owner request 2026-10-06, from notes/research/u-testing-audit.md: rule tests assert U's outcomes, amending D103: outcome classes fire, clean, unresolved, notapplicable (grl-spec.md 9, one grammar project-wide); clean is certified over at least one examined subject; markers include advisory and unresolved[reason] and strictness counts them; required cases per polarity, tier and must_measure checked by coverage; universal rules tested across fidelity classes with expectations derived from needs and capability cells; fidelity measured from the corpus; fix invariants include parse status and class preservation. An artifact with no adapter is Unresolved (reason fidelity, rolled up per rule and language) for capability rules, NotApplicable only for binaries and declared-featureless languages

### D98

Owner request 2026-10-06: tests and CI modelled on ruff and ty: mdtest snapshot-diagnostics, per-rule fixtures with a registry coverage test, fix snapshots with fixpoint convergence, inline parser tests, formatter idempotence, snapshot hygiene, an ecosystem check over a pinned corpus, cargo-fuzz targets built on every PR, deterministic instruction-count PR benchmarks, change detection, and deny, shear, typos and MSRV steps, all as `cargo dev ci` steps

### D103

Owner request 2026-10-06 (match ruff and ty closely), from the source review notes/research/rule-testing.md: mdtest is the primary rule test (ruff moved to the shared mdtest crate ty uses), with strict markers (unmatched findings fail; optional column and message), sections with multi-file cases and toml config, inline snapshot blocks with an update env, and the rendered diagnostic showing the fix diff; ruff's fix invariants run automatically for every fixable case; rule docs are mdtest files (ty lint_docs); fixtures plus insta only for large inputs; panics are contained with expect-panic; unknown directives and attributes are parse errors; frob keeps its fire-and-clean controls and shrink-only coverage allowlist

Also logged against: crates/gob-mdtest/FORMAT.md.

### D122

Owner 2026-10-08 ("aren't retreading the work of ty and ruff"): frob never reimplements a single-language rule a maintained tool ships; bound tools run as pinned subprocesses (no linked crates: ruff crates are internal with no semver, ty 0.0.x, oxlint and Biome linter crates unpublished), output SARIF or native JSON with source_rule, project config read never rewritten, fixes and suppressions owned by the tool; tool definitions are data in the std pack; oxlint is the JS/TS default with ESLint as escape hatch; language facts stay in gob, type facts via ty server LSP and a typescript6 helper behind a latency spike
