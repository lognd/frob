# strata: coverage totality (T-0341 epic)

This file is the `docs/modules/strata.md` doc-edge home the T-0341 epic's
child tickets declare in their `scope` (`tickets.md` T-0341, T-0667, and
siblings). The detailed SYS100-102 self-conformance mechanism (grammar,
gap statements, waiver shape) lives in `docs/strata/selfconform.md` --
this file adds only what T-0667's own scope covers and does not duplicate
that page.

<a id="sys-cov-coverage-totality-sys103-t-0667"></a>
## SYS-COV coverage totality (SYS103, T-0667)

<!-- frob:invariant INV-048 -->

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
audited, with no `src/frob/`-specific path assumption -- INCLUDING frob's
own tree, as of T-1091 (`_coverage_totality_scan_prefix` used to restrict
it to `_PACKAGE_ROOT` there, same as SYS102; see "Restriction dropped for
real" below).

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

### Registry cross-reference (closed)

`docs/design/registry/check-coverage.yaml` now carries a `CHK-GATE-SYS103`
entry (`check-coverage.yaml:973`) alongside `CHK-GATE-SYS100`/
`CHK-GATE-SYS101`/`CHK-GATE-SYS102`, and `_selfconform.py` carries the
matching `frob:enforces CHK-GATE-SYS103` directive -- the follow-up filed
against T-0667's registry-cross-reference gap has since landed.

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

### Restriction dropped for real (T-1091)

T-1091 closes the follow-up the previous section named:
`_coverage_totality_scan_prefix` now ALWAYS returns `None` -- the
`_PACKAGE_ROOT` carve-out is gone, not just modeled around. The live
`SELFAUDIT001` gate (`frob sys audit`, `frob check --only sys`) now
scans the WHOLE repo tree on every run, frob's own included, exactly
like the general (non-frob) case always did. This is safe precisely
because of what the previous section modeled: `design/frob.strata`
already declares real `code=`/`may` for `tests/**`, `scripts/**`,
`frob-core/src/**`, and `strata-core/src/**`, so dropping the
restriction produces zero NEW findings on this repo's own `frob check`
-- `TestRealGateGreen::test_repo_design_and_declarations_are_self_
conformant` now exercises this directly (no monkeypatch needed), and
`TestCoverageTotality::test_repo_unrestricted_scan_is_clean` keeps
independently pinning the same zero-violations claim against a forced
`None` prefix in case `_coverage_totality_scan_prefix` is ever
re-restricted later. If a genuinely new, still-unmodeled tree is added
to this repo in the future, SYS103 will correctly go non-zero on it --
that is the detector doing its job, not a regression to patch around.

<a id="sys104-interface-conformance-t-0668"></a>
## SYS104 exact interface conformance (T-0668)

`docs/design/structural-linter-adversarial-hardening.md`'s "undeclared
public surface" evasion row -- T-0341's acceptance criterion [1]. A node
declares its public interface with one `interface=<symbol>` attr per
symbol (`Node.attrs`, same opaque-string convention `code=`/`managed`
already use, T-0078/T-0172; no `.strata` grammar change). SYS104 requires
the declared set to EQUAL the real public surface of the node's own
`code=`-bound `.py` files: a real export missing from `interface=` fires,
and an `interface=` entry with no matching real export fires. The real
surface is `__all__`'s literal contents if the module declares one, else
every non-underscore-prefixed top-level `def`/`class`/assignment target.

### Mandatory as of T-1113 (closes the original scope cut)

SYS104 used to evaluate only a node that had ALREADY declared at least
one `interface=` attr -- an opt-in scope cut disclosed at T-0668, because
making it mandatory required adding real `interface=` declarations to
`design/frob.strata` itself, out of T-0668's own `scope`. T-1113 closes
that gap directly: `design/frob.strata` now carries a real, measured
`interface=<symbol>` attr for every node whose bound code has a non-empty
public surface (one attr per real symbol, generated from the same
`_module_public_symbols`/`_node_real_public_surface` the check itself
uses, so declared and real start out in agreement), and SYS104 now
evaluates ANY node whose real surface is non-empty, whether or not it has
declared anything -- a node with nothing declared and a non-empty real
surface fires (every real symbol reports as missing), exactly like a
node that declares some but not all of its surface. A node with an EMPTY
real surface (no bound `.py` files, or files exporting nothing) stays
exempt either way -- there is no obligation to declare an interface for
code with nothing to declare. Python-only, the same boundary `bind_code`
itself already draws.

<a id="sys105-purpose-contract-t-0669"></a>
## SYS105 purpose contract (T-0669)

The design doc's "purpose drift" row (a "logging" module that opens
sockets) -- T-0341's acceptance criterion [2]. A node declares
`purpose=<profile>` (at most one, same opaque-attr convention); the
profile names a fixed, closed allowed-effect vocabulary
(`_PURPOSE_PROFILES` in `src/frob/strata/_selfconform.py`: `pure`,
`read-only`, `logging`, `network`, `full`). Any observed effect kind
outside the declared profile's allowed set fires (the SAME normalized
observed-kind union SYS101 already computes, reused not duplicated). An
unrecognized profile name is itself a finding -- a typo is never treated
as the permissive `full` profile.

Disclosed scope cut, UNCHANGED by T-1113 (which flipped only SYS104, per
that ticket's own declared follow-up -- see T-1113's Done report for why
SYS105/SYS106 stayed opt-in): only a node that has declared `purpose=` is
checked; mandating it repo-wide is filed follow-up work, for the same
`design/frob.strata`-declaration-effort reason SYS104 used to carry.

<a id="sys106-binding-totality-t-0670"></a>
## SYS106 binding totality / laundering (T-0670)

The design doc's "binding laundering" row: "node binds to file X, real
logic sits in unbound file Y" -- T-0341's acceptance criterion [3].
SYS103 already flags any `FOREIGN` file with an observed capability, but
only within its scan prefix (`_coverage_totality_scan_prefix`,
`_PACKAGE_ROOT`-restricted on frob's own tree). SYS106 closes the
specific reachability-laundering evasion prefix-independently: starting
from every bound node's own `.py` files, it follows resolved local
python imports (`frob.lang.resolve_local_import`, cycle-safe BFS) to
build the full reachable-file closure, then fires once per reachable
`FOREIGN` file that `scan_file_capabilities` observes any capability in
-- regardless of whether that file falls inside SYS103's own scan
prefix. A capable file only SYS103's blanket (prefix-restricted) pass
would catch, but that is NOT reachable from any bound node, does not
fire SYS106 (it is not the specific "laundered from a bound node" threat
SYS106 targets, even though it may still be a genuine SYS103 finding on
its own).

### Verification against the live repo

`tests/unit/strata/test_selfconform.py::TestRealGateGreen::
test_repo_design_and_declarations_are_self_conformant` runs SYS106 (via
`check_self_conformance`) against `design/frob.strata`'s real
declarations and the real `src/frob/` tree and asserts zero violations
-- measured directly, not assumed: since SYS103's own unrestricted-scan
regression test (`TestCoverageTotality::
test_repo_unrestricted_scan_is_clean`) already proves zero FOREIGN-and-
capable files exist anywhere in the repo (prefix bypassed), SYS106's
reachable subset of that same empty set is necessarily also empty.

<a id="bounded-escape-hatches-t-0671"></a>
## Bounded escape hatches for conformance obligations (T-0671)

T-0341's fifth acceptance criterion: every conformance waiver
(SYS104/SYS105/SYS106) must be reason-required (already true, T-0174's
grammar-mandatory `reason`), staleness-dated, and visible in an
un-droppable floor view -- never a permanent silent exemption.

### Staleness dating: `expires:YYYY-MM-DD`

The `.strata` `waive` clause's grammar has no expiry field (adding one is
a grammar change, out of this ticket's scope). `_waive.py::
parse_waiver_expiry` is the in-scope substitute: an `expires:YYYY-MM-DD`
substring embedded anywhere in the already-mandatory `reason` string,
e.g. `waive "SYS105:net.connect" reason "tracked debt, expires:2026-12-
31" ticket "T-1234";`. A SYS104/SYS105/SYS106 waiver with NO `expires:`
marker, or one whose date has passed, is EXPIRED:
`_selfconform.py::_apply_conformance_waiver_staleness` moves its finding
back into `violations` (the underlying obligation re-fires, unchanged
from having no waiver at all) and adds a new `SYSWAIVE003`
(`CONFORMANCE_WAIVER_EXPIRED_RULE`) finding naming the expired waiver.
Every OTHER waiver family (SYS100-103, THREAT002/003, LINT004, ...) is
untouched by this gate -- it applies only to the three conformance
checks T-0668/T-0669/T-0670 built.

### SYS104/SYS105 join `MULTI_INSTANCE_WAIVER_FAMILIES`

Both can fire more than once per node (once per undeclared/missing
interface symbol, once per observed effect kind outside the purpose
profile), so a `waive` clause on either MUST carry a `RULE:SUBTARGET`
sub-target (`waive "SYS104:secret_backdoor" ...`, `waive
"SYS105:net.connect" ...`) -- a bare `waive "SYS104"`/`waive "SYS105"`
is an elaborate-time `MalformedWaiver` error, same discipline SYS100/
SYS101/THREAT002/THREAT003 already established. SYS106 is NOT in this
set -- it fires once per unbound FILE (like SYS103), not once per node,
so it keeps the bare-rule form.

### Floor view: un-droppable by construction

`report.waived` already carries every currently-active (unexpired)
conformance waiver with its reason folded in (`_fold_waived_violations`,
the same "waived, never silently dropped" mechanism every other SYS
family already uses) and `sys_runner.py` prints it UNCONDITIONALLY on
every `frob sys audit` run, never behind a flag -- so an active
conformance waiver cannot be hidden from default output without editing
the printing code itself, which is exactly the "cannot be hidden from
default output" acceptance criterion.

<a id="hardening-doc-denominator-totality-t-0672"></a>
## Hardening-doc denominator totality (T-0672, T-0341 epic close condition)

`tests/unit/strata/test_structural_linter_hardening_totality.py` binds
`docs/design/structural-linter-adversarial-hardening.md`'s full corpus
denominator (5 named principles + 9 arch-evasion rows + 9 strata-evasion
rows, `docs/design/registry/arch-checks.yaml`'s `SLH-RULE-*`/
`SLH-ARCH-EVA-*`/`SLH-SYS-EVA-*` ids) to the registry, real-data (not
fixture) style, mirroring the `tests/test_registry_reconciliation_*.py`
sibling pin tests: every denominator id must resolve to a real registry
entry with a non-`UNDISPOSITIONED` disposition, and the registry must
carry no `SLH-*` id the denominator does not know about either (both
directions of the N:M totality claim).

The five `SLH-SYS-EVA-01..05` rows (unmodeled module / under-declared
capability / undeclared public surface / purpose drift / binding
laundering) are additionally re-dispositioned from a generic
`out_of_scope:none` reasoned-deferral to `handled_by:SYS103`/`SYS100`/
`SYS104`/`SYS105`/`SYS106` respectively -- addressed-by-check, now that
T-0667-T-0670 built a real registered rule for each. `check_self_
conformance` carries the matching `frob:enforces SLH-SYS-EVA-0N-...`
directives (REG008's "the disposition names a real code site" half).
The other 18 denominator rows (the 5 design PRINCIPLES and the arch-
evasion/remaining strata-evasion rows) stay as their existing, honest
reasoned-deferral dispositions -- they motivate gate DESIGN holistically
(the waiver/debt/deprecation escape-hatch families, fail-closed posture)
rather than naming one bindable rule, and forcing a `handled_by:` there
would be a false, over-narrow claim.
