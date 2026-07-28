# strata: coverage totality (T-0341 epic)

This file is the `docs/modules/strata.md` doc-edge home the T-0341 epic's
child tickets declare in their `scope` (`tickets.md` T-0341, T-0667, and
siblings). The detailed SYS100-102 self-conformance mechanism (grammar,
gap statements, waiver shape) lives in `docs/strata/selfconform.md` --
this file adds only what T-0667's own scope covers and does not duplicate
that page.

<a id="sys-cov-coverage-totality-sys103-t-0667"></a>
## SYS-COV coverage totality (SYS103, T-0667)

`frob sys audit`'s self-conformance family (`src/frob/strata/_selfconform.py`)
gains a fourth rule, SYS103, whose finding label is "SYS-COV" --
`docs/design/structural-linter-adversarial-hardening.md`'s "un-modeled
module" row and the T-0341 epic's acceptance criterion [0]: "every
deployable/public module -- and every module the binding-aware scanner
finds ANY capability in -- must bind to exactly one strata node;
unbound-but-capable code is a hard failure." Same posture as COV001 for
missing documentation: a capable module that escapes the `.strata` model
escapes every downstream obligation this repo can express, so leaving it
un-modeled cannot be a silent pass.

### Why SYS103, not just SYS102

SYS102 ("unmodeled code", `docs/strata/selfconform.md#the-three-rules`)
already flags every `FOREIGN` file inside `src/frob/` -- but it is
hardcoded to `_PACKAGE_ROOT` ("src/frob"), frob's own package layout
(T-0211). Every other repo `frob sys audit` runs against structurally
lacks `src/frob/`, so SYS102 is permanently, silently vacuous there --
exactly the evasion the T-0341 epic exists to close. SYS103 is the
repo-general form: it runs over the SAME `_capability_binding` superset
(`bind_code` + the T-0169 non-Python extension) on WHATEVER root is
audited, with no `src/frob/`-specific path assumption -- EXCEPT on frob's
own tree, where `_coverage_totality_scan_prefix` restricts it to
`_PACKAGE_ROOT`, same as SYS102 (see "Known gap" below for why).

### Rule

A `FOREIGN` file (no node's `code=` glob claims it) for which
`frob.vet._capability.scan_file_capabilities` (T-0328's import/binding-
aware resolver -- not a bare substring guess) observes at least one
capability fires SYS103 once, naming the file and the observed capability
kind(s) in its `detail`. A `FOREIGN` file with zero observed capabilities
(pure data, a re-export-only `__init__.py`) does not fire -- it carries no
dangerous effect escaping an obligation, so it is not the failure mode
SYS-COV exists to catch. A file bound to any real node never fires SYS103
regardless of what it does (SYS100/SYS101 already reconcile a BOUND
file's declared-vs-observed capabilities; SYS103's only question is
binding, not conformance).

### Waiving

SYS103 has no per-capability-kind sub-target (unlike SYS100/SYS101):
the finding is about the whole FILE having no owner, not one specific
kind of it. It is not in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, so
it takes the bare-rule waiver form: `waive "SYS103" reason "..." ticket
"T-...";` -- same shape as SYS102's.

### Known gap: registry cross-reference

`docs/design/registry/check-coverage.yaml`'s `CHK-GATE-SYS100`/
`CHK-GATE-SYS101`/`CHK-GATE-SYS102` entries record each sibling rule as "a
live, enforced gate rule". A matching `CHK-GATE-SYS103` entry (and the
corresponding `frob:enforces CHK-GATE-SYS103` directive on
`check_self_conformance`) was NOT added by T-0667: `docs/design/
registry/**` is outside this ticket's declared `scope`. Filed as a
follow-up so the registry cross-reference does not silently lag (see
T-0667's Done report for the filed ticket id).

### Modeled: `_PACKAGE_ROOT` restriction's 264-finding follow-up (T-1079, closed)

T-0667 shipped `_coverage_totality_scan_prefix` restricting SYS103 to
`_PACKAGE_ROOT` ("src/frob") specifically when auditing frob's own tree,
because an unrestricted whole-`root` scan surfaced 264 real,
then-unmodeled findings under `tests/**`, `scripts/**`,
`frob-core/src/**`, and `strata-core/src/**` (measured 2026-07-28) --
`design/frob.strata` had only ever declared `code=`/`may` for
`src/frob/`, so wiring the unrestricted scan in directly would have
regressed the live `SELFAUDIT001` gate from green to 264 errors.

T-1079 closes that gap by modeling all four trees honestly, rather than
excluding them: `testsuite` (`code "tests/**"`), `scripts_ops`
(`code "scripts/**"`), `strata_core_native` (`code "strata-core/src/**"`),
and `frob_core_native` (`code "frob-core/src/**"`), each with `may`
declarations measured directly against
`frob.vet._capability.scan_file_capabilities`'s own per-file output for
the unrestricted scan -- none of the four trees was a "reasoned
exclusion" candidate, since every one of them genuinely exercises real
capabilities (the test suite spawns subprocesses and writes fixture
files by design; the release script edits `pyproject.toml`; both Rust
crates cross the FFI boundary). Re-running the SYS103 scan with
`_coverage_totality_scan_prefix`'s restriction bypassed (i.e. simulating
the fully-unrestricted scan `_PACKAGE_ROOT` exists to defer, T-1079 Done
report has the exact command) against the now-updated `design/
frob.strata` returns zero SYS100/SYS101/SYS102/SYS103 violations --
`tests/unit/strata/test_selfconform.py::TestCoverageTotality::
test_repo_unrestricted_scan_is_clean` locks this in as a regression
test. `_coverage_totality_scan_prefix` itself (`src/frob/strata/
_selfconform.py`) was out of T-1079's declared `scope` and is left
unchanged -- the live `SELFAUDIT001` gate still runs the `_PACKAGE_ROOT`-
restricted scan in production, so this modeling work does not yet widen
what the LIVE gate itself checks on every `frob check` run; wiring the
gate to drop the restriction now that the model has zero findings
either way is real, disclosed follow-up work (see T-1079's Done report
for the filed ticket id), not done by this ticket.
