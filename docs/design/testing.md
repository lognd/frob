# Testing rules against the universal model (D106)

Status: current
Owner: gob
Decisions: D106, D103
Audience: rule author

Provenance: accepted, coordinator decision 2026-10-06 (owner: "make sure the
lints, mdtests, snapshots and so forth are designed with [the universal
model] in mind"). Evidence: notes/research/u-testing-audit.md (the audit
of D103 against U), notes/research/rule-testing.md (ruff, ty, clippy,
biome, oxc, rust-analyzer). Amends D103: ruff and ty test a two-valued
world (a case has diagnostics or not); U is not two-valued
(universal-model.md 4.1, 4.2), so the harness asserts U's outcomes, not
only the presence of findings.

## 1. Outcome classes

Every test case expects exactly one class, the vocabulary of grl-spec.md
section 9, shared by gob-mdtest, GRL examples and the grimble-bind corpus
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

## 2. Markers and strictness

Markers name the severity or class: `error:`, `warn:`, `advisory:`,
`unresolved[REASON]:` (optionally `required`), with optional column and
message text. A finding with no span (a rolled-up Unresolved, a repo-scope
finding) is asserted by a header expectation on the case.

Strict mode (ty's "unexpected error") counts every class: an Unresolved
or Advisory finding of a selected rule that no marker matches fails the
case, so a corpus author can never silence honesty to make a test pass.

## 3. Required cases per rule

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
| tier Universal | the language matrix of section 4 |
| lexical rule (`needs = Lexical`: text, literals, prose only) | `opaque_fire`: an `expect=fire cell=island` block, a `fire` inside an opaque region, beside an `unresolved` structural rule over the same region |

Each rule's fire and clean cases live in one suite file.

## 4. The language matrix for universal rules

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

## 5. Fidelity is measured, not claimed

An adapter's fidelity level is derived from its conformance corpus
(universal-model.md 3.3: F1 units and containment, F2 Must lexical edges,
F3 apply edges with declared status, F4 attributes, bound comments,
regions and phases); the test fails when the declared level differs from
the measured one in either direction. Every adapter ships a capability
matrix snapshot, a garbage-input case (no panic; Unresolved or
NotApplicable) and a partial-parse case. `frob doctor --languages`, the
languages page and the README table are generated from the same data.

## 6. Fixes and snapshots

The fix invariants run for every case with a fixable finding (ruff's
harness): a fixpoint within 10 rounds, a reparse after each round with
parse status and opaque or hole counts never degrading, no fixable finding
left, and no finding changing class from `fire` to `unresolved` (a fix
that hides code inside a macro or an opaque region fails).

Snapshots render the outcome class, the Unresolved reason in words and its
remedy, and the fix diff with its tier. The snapshot update mode never
changes a case's outcome class silently; a class change needs an explicit
second switch.

## 7. Polarity conformance and the ecosystem layer

A standard small repository per polarity (a May-only edge, a Must edge,
an opaque region, an Unknown visibility) is run against every shipped
rule, so "the rule behaves as its declared polarity says" is a test, not a
claim (universal-model.md 4.5, Theorem 3: never an Error or Warn whose
premise is false). The ecosystem check (build-test-ci.md 6) reports files
and subjects examined per rule and language, and a drop in subjects
examined is a regression even when the finding count falls.

## 8. Incompleteness: the oracle column (cohesion.md 2.3)

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
  examined, section 7);
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

## 9. Native coverage providers

Native coverage is one shared pipeline with one per-language seam. Sections
9.1 to 9.4 describe the contract, the registry, the flag and the threshold knob;
9.5 lists the shipped languages. The source of truth is the module docs of
`frob_evidence::coverage` (`crates/frob-evidence/src/coverage/mod.rs`).

### 9.1 The CoverageProvider contract

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

### 9.2 The PROVIDERS registry

`PROVIDERS` (`&[&dyn CoverageProvider]`, in `coverage/mod.rs`) is the only list of
languages. Its entries, in order, are `rust::RustCoverage` (nextest),
`python::PythonCoverage` (pytest), `js::VitestCoverage` (vitest),
`js::JestCoverage` (jest) and `csharp::CsharpCoverage` (dotnet). `registered(provider)`
returns the entry whose `provider()` matches. A test provider with no entry,
such as `unity`, is recorded `NotRun` with the reason "no coverage provider is
registered for <provider>". COV004 reads the same registry. Adding a language is
one new module under `coverage/` and one `PROVIDERS` entry.

### 9.3 The --coverage flag

`frob ticket evidence add <ticket> --provider <p> --ref <filter> --coverage` runs
the tests first and then the provider's coverage command, and records the
per-language summary on the evidence record. A coverage failure never fails the
capture. The flag belongs to test-runner providers only: `file`, `attestation`
and `command` are rejected with a usage error. `unity` is accepted but has no
registered provider, so it records `NotRun`. `frob test` has no `--coverage`
flag; coverage is captured only through `ticket evidence add`.

### 9.4 The [coverage] require_reports knob

`[coverage] require_reports` (boolean, default `true`, enforcement) is read by
COV004 in `frob-obligations`. When it is true, each registered provider whose
language `has_tests` and has no `.frob/coverage/<language>.info` yields one COV004
finding: an Unresolved "not run" finding when the tool is not installed, otherwise
a "has tests but no coverage report" finding. When it is false, neither finding is
produced, and the `threshold` checks still run. The check looks at the
per-language file, not at the evidence record's status. The file COV004 reads is
`[coverage] report` (default `lcov.info`). Key reference:
[config.md](../reference/config.md).

### 9.5 Per-language providers

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
