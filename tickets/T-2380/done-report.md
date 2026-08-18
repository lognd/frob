## Done report

## SYS003 calibration verdict (measured 2026-08-18, not a burn-down -- decision record only)

Sampled the full `--json` capture from the T-0969 denominator run (not a
fresh 15-20 grep sample -- aggregated + spot-read across every
(from_component, to_component) pair present, since the whole population
was already in hand from the epic measurement). This is (b), not (a):
the gate is substantially over-firing, not surfacing 4834 genuine
undeclared architecture violations.

**95.4% (4610 of 4834) of all findings are `testsuite -> *`** -- test
files importing the production modules they exercise. Examples:
- tests/_write_unchecked.py:24 imports frob.tickets._models
  (testsuite -> tickets_ledger)
- tests/conftest.py:5 imports frob.lang (testsuite -> graphlang)
- tests/gates/test_bug_repro_at_ref_public.py:16 imports frob.gates
  (testsuite -> gates)
- tests/system/test_cli_doctor.py:106 imports frob.doctor
  (testsuite -> cli)
- tests/test_capability_registry.py:16 imports frob.vet._capability
  (testsuite -> vet)

This is not architecture drift -- a test suite importing across every
component it tests is the expected, correct shape of a test suite, not
a violation the "declare a Flow or remove the import" remediation makes
sense for. Declaring one Flow per (testsuite -> component) pair for
every component under test is not meaningfully different from a
blanket "testsuite may import anything" exemption, except spread across
16 separate declarations. Either SYS003 needs a structural testsuite
exemption (the gate already has a `testsuite` component in its own
model, per every finding above -- it clearly CAN identify test code, it
just isn't given a pass for the expected direction), or a single bulk
Flow declaration covering testsuite -> * is the right fix -- not one
per finding.

**The remaining 224 findings (4.6%) are production-code cross-component
imports, and even here roughly 38% (86/224) cluster on a small set of
modules that read as misclassified shared utilities rather than real
per-import violations**: frob.excludes (50 hits, flagged from gates,
core, and vet all importing it -- e.g.
src/frob/gates/__init__.py:58, src/frob/bind/__init__.py:7,
src/frob/vet/_capability_scan.py:26, all "-> cli"), frob.logging (22
hits, flagged from refactor and verify -- e.g.
src/frob/refactor/_apply.py:16, src/frob/verify/_attribution.py:65,
both "-> core"), plus frob.yaml_io/frob.tomlio/frob.gitio (6+4+4=14
more). A module that half a dozen unrelated components all need to
import (a shared exclude-pattern helper, the logging setup, generic
file-format I/O) is exactly the shape of a cross-cutting utility that
usually gets its own architecture tier (e.g. "shared"/"util") exempt
from directional Flow declarations, not a component that every caller
must individually declare a Flow toward. Whether frob.excludes/
frob.logging/frob.yaml_io/frob.tomlio/frob.gitio are currently modeled
as owned by "cli"/"core" (plausible misclassification) or genuinely
belong there (in which case the 86 importers really do need
declarations) was NOT independently verified against the architecture
model this run -- that check is exactly the next step, not something to
guess at from the check output alone.

The remaining ~138 findings (224 - 86) look like a mix of plausibly
genuine cross-component imports (e.g. refactor -> core, verify -> core,
tickets_ledger -> graphlang, cli -> verify) that would need real
per-case judgment -- some may be legitimate Flow gaps, this sample did
not attempt to adjudicate each one.

**Verdict: (b), gate over-firing, on both halves.** The testsuite
direction (95.4% of volume) is not a real signal at all and should be
structurally exempted before anything else happens. The 224 remaining
production findings should NOT be bulk-declared as Flows either --
first re-classify frob.excludes/frob.logging/frob.yaml_io/frob.tomlio/
frob.gitio (and any other 3+-importer utility module in the tail) as
shared/cross-cutting rather than owned-by-one-component, THEN
re-measure what's left before deciding whether the true remainder
(plausibly under 150) is a single-dispatch burn-down or needs further
splitting. Do NOT start a 4834-finding burn-down against the current
gate calibration -- most of it should disappear before a single Flow
declaration is hand-written.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
