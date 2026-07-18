# frob sys

Applications of the strata design model (`docs/strata/roadmap.md` "CLI
surface (target)"). Four verbs today: `plan` (T-0084, obligation ->
ticket compiler), `doc` (T-0085, threat-catalog audit matrix), `export`
(T-0086, k8s/seccomp/IAM config skeletons), and `audit` (T-0115, the
checking counterpart to `doc`). `check`/`trace`/`capacity`/`threats` are
later phase-5 tickets not yet landed on `main` -- when they land, this
doc and `src/frob/app/sys_runner.py` extend rather than get replaced.

## Quickstart (T-0167)

Every `frob sys <verb>` (except `export`) takes a **design root**, not a
single file: a directory (default `.`) containing one or more `.strata`
design files under its `design/` subdirectory (or `[strata].design_dir`
in `frob.toml`). Point the command at the repo root, not at
`design/frob.strata` directly:

```bash
frob sys plan design/            # dry-run: print the would-be ticket tree
frob sys plan design/ --apply    # write the planned tickets
frob sys doc design/             # threat-catalog audit matrix (owasp-top-10)
frob sys audit design/           # check per-family exhaustiveness, exit nonzero on gaps
```

`export` is the one exception: it takes a **path to a single `.strata`
file** (default `design/frob.strata`), since a config skeleton is
rendered from one elaborated `KernelModel`, not a directory of models:

```bash
frob sys export design/frob.strata --format seccomp
```

`frob sys --help` (and each verb's own `--help`) repeats this
distinction inline as an epilog -- see `_add_sys_parser` in
`src/frob/__main__.py`.

## `frob sys plan`

Reads every `.strata` design file under the repo's design dir (default
`design/`, or `[strata].design_dir` in `frob.toml`), computes the
**obligation frontier**, and compiles it into a ticket tree:

- **unrefined** -- an `abstract` component with no matching `refine`
  block (docs/strata/surface.md#refinement-hierarchical-models: "the
  unrefined frontier is exactly the planning frontier"). One parent
  ticket ("Refine abstract component X") plus one child ("Decompose X
  via refine block"), scoped to the component's `code=` globs.
- **refuted** -- a claim `evaluate_claims` returns `Verdict.REFUTED` for.
  One bug ticket, scoped to the counterexample path's bound code.
- **threat** -- a `THREAT003` violation: a fired capability obligation
  with no discharging claim at the required rung. One security ticket
  per (node, CWE) pair.
- **unbound** -- a `boundary`/`secret` construct with no
  `frob:boundary`/`frob:secret` code directive anywhere (the SYS002
  question). One security ticket per construct.

### Usage

```bash
frob sys plan                 # dry-run: print the would-be ticket tree
frob sys plan --apply         # write the tickets to tickets.md
frob sys plan /path/to/repo   # plan a different repo root
```

Dry-run is the default deliberately -- a plan is a proposal, not a
side-effecting command, until `--apply` says otherwise.

### Idempotency

Every planned ticket's body carries exactly one `sys-plan:<construct-
qualname>:<obligation-kind>` marker line. `frob sys plan` diffs the
freshly compiled marker set against every marker already present in some
ticket's body (open or closed) before writing anything: re-running
against an unchanged model creates nothing new, and re-running after a
model change creates only the delta (the new/changed markers). A ticket
is never re-created after being closed, since the marker matches
regardless of ticket state -- closing a sys-plan ticket is the discharge
signal, not a re-open trigger.

### Public API

<!-- frob:describes src/frob/strata/_plan.py::plan_obligations -->
<!-- frob:describes src/frob/strata/_plan.py::PlannedTicket -->
<!-- frob:describes src/frob/strata/_plan.py::PlanResult -->
<!-- frob:describes src/frob/strata/_plan.py::MARKER_PREFIX -->

```python
from frob.strata import load_design_ids, plan_obligations

ids = load_design_ids(root)
model = ids.models[0]
result = plan_obligations(model)
for ticket in result.tickets:
    print(ticket.marker, ticket.title)
```

## `frob sys doc`

Renders the per-family threat-catalog audit matrix (docs/strata/threat.md
#the-exhaustiveness-proof-the-point) for a selected baseline view against
every `.strata` design file under the repo's design dir: applicable
weakness -> precondition present? -> mitigation -> evidence rung/status ->
citation, grouped by `WeaknessEntry.family`, plus an out-of-scope section
and a catalog-gaps (THREAT001) section when either is non-empty. Output is
deterministic markdown to stdout.

```bash
frob sys doc                       # matrix for the owasp-top-10 view
frob sys doc --view owasp-top-10   # explicit view
frob sys doc /path/to/repo
```

<!-- frob:claims owasp-top-10 -->
This command's own design model (`design/frob.strata`, T-0081
self-hosting) claims the `owasp-top-10` exhaustiveness result above is
PROVED -- the DOC003 gate (below) checks that claim on every `frob check`
run, so this line can never silently drift from what the model actually
proves.

### The claims audit (DOC003)

`frob:claims <view>` is a marker directive in any doc page: it asserts
that `<view>`'s exhaustiveness result (docs/strata/threat.md, "the
exhaustiveness proof is computed PER FAMILY against a cited baseline") is
PROVED against the current design model. `frob check`'s `sys_gate`
verifies every such marker: an unproved claim (a live THREAT001/002/003
violation for that view) is a DOC003 error naming the failing
obligation(s); an unknown view name is also a DOC003 error. DOC002 was
already taken (anchor resolution, T-0127) by the time this landed, hence
DOC003 for the claims audit -- see docs/strata/threat.md's charter-drift
note. Suppressed, like SYS001, while any `.strata` design file fails to
load.

### Public API

<!-- frob:describes src/frob/strata/_sysdoc.py::render_audit_matrix -->
<!-- frob:describes src/frob/strata/_sysdoc.py::audit_claim -->
<!-- frob:describes src/frob/strata/_sysdoc.py::ClaimAuditResult -->
<!-- frob:describes src/frob/strata/_sysdoc.py::merge_models -->

## `frob sys export`

Render a runtime-enforcement config skeleton from a `.strata` design's
elaborated `KernelModel`. The model already proves architecture-level
claims statically (phase 0-4); exporting to real enforcement planes means a
static proof is backed by defense-in-depth that cannot silently diverge
from the declared design.

### Usage

```bash
frob sys export --format k8s design/frob.strata        # k8s NetworkPolicy YAML
frob sys export --format seccomp design/frob.strata     # seccomp profile JSON
frob sys export --format iam design/frob.strata         # IAM policy JSON
frob sys export --format k8s                             # defaults to design/frob.strata
```

Output is always deterministic (sorted keys, stable node/flow ordering) so
two exports of the same model are byte-for-byte identical -- this is what
makes exports diffable in review and CI-checkable against a golden fixture
(`tests/unit/strata/test_export_golden.py`, run against frob's own
self-hosting model, `design/frob.strata`, T-0081).

### k8s NetworkPolicy

One `NetworkPolicy` document per component `Node`, deny-by-default (kernel
law 2): ingress is allowed only from nodes with a declared `Flow` into it,
egress only to declared `Flow` targets. A `Flow` whose peer is a
foreign-trust node (e.g. `registry` in `design/frob.strata`) has no
in-cluster pod to select -- that peer is recorded as a
`frob.strata/foreign-peer` annotation rather than silently dropped or
silently allowed from anywhere.

### seccomp profile skeletons

One profile per `Node`, `SCMP_ACT_ERRNO` default (deny unlisted syscalls).
Allowed syscalls are a fixed baseline (`exit`, `read`, `write`, ...) plus
whatever a declared `may` capability KIND maps to:

| `may` KIND | syscall family allowed |
|---|---|
| `exec` | `execve`, `execveat`, `fork`, `vfork`, `clone` |
| `net` | `socket`, `connect`, `bind`, `listen`, `accept`, `sendto`, `recvfrom` |
| (any other kind, or none) | baseline only |

The KIND of a `may` atom is the segment before its first `.` or `:`
(`"net.out:stripe.com"` -> `"net"`), the same extraction
`_effects.py::_may_kind` already uses for tier-2 capability conformance
(no duplicated rule). **This mapping is deliberately coarse (v0)**: a
capability KIND names a class of effect, not an exact syscall list. Do not
treat an exported profile as a substitute for a real syscall audit --
treat it as a starting skeleton to tighten by hand.

### IAM policy skeletons

A generic, provider-agnostic JSON document (no AWS/GCP/Azure-specific
grammar) with two `Allow` statements per declared `Flow`: a `write`
statement (the flow changes the destination's state) and a `read`
statement (the flow's caller reads whatever response the destination
returns), `principal` = `Flow.src`, `resource` = `Flow.dst`. Flow
direction is the only signal the kernel model carries for IAM action
inference today; a real read-vs-write split needs an explicit flow
attribute the surface grammar does not yet express (follow-up, not this
ticket's scope).

### Public API

<!-- frob:describes src/frob/strata/_export.py::export_k8s_netpol -->
<!-- frob:describes src/frob/strata/_export.py::export_seccomp -->
<!-- frob:describes src/frob/strata/_export.py::export_iam -->

```python
# frob/strata/_export.py
def export_k8s_netpol(model: KernelModel) -> str
    # One deny-by-default NetworkPolicy YAML doc per component Node.

def export_seccomp(model: KernelModel) -> str
    # One seccomp profile skeleton (JSON) per Node, may-capability-derived.

def export_iam(model: KernelModel) -> str
    # One generic IAM policy document (JSON), two statements per Flow.
```

## CLI wiring

<!-- frob:describes src/frob/app/sys_runner.py::run -->
<!-- frob:describes src/frob/app/sys_runner.py::_run_doc -->
<!-- frob:describes src/frob/app/sys_runner.py::_run_export -->

## `frob sys audit`

The CHECKING counterpart to `frob sys doc`'s human-facing matrix: evaluates
the full three-part exhaustiveness conjunction (docs/strata/threat.md#the-
exhaustiveness-proof-the-point) -- THREAT001+002+003 for the security AND
quality families, COMPLIANCE001+002 for compliance -- against EVERY
configured baseline view for every `.strata` design file under the repo's
design dir, and exits nonzero with a named-gap summary (family, view,
rule, detail) when any part fails. Zero new detection: composed entirely
from the already-shipped `check_catalog_completeness` / `check_capability_
completeness` / `check_discharge_completeness` / `evaluate_compliance`
calls `frob sys doc` and `evaluate_threats` already make.

```bash
frob sys audit                 # every default view, every family
frob sys audit /path/to/repo
```

Default views: every entry in `VIEWS` (security), `QUALITY_VIEWS`
(quality), and `REGULATION_VIEWS` (compliance) -- so a clean run proves
exhaustiveness against every baseline the repo's catalogs currently ship,
not just one. CI-parseable output: one `GAP family=... view=... rule=...
detail=...` line per violation, `PROVED` on a clean run.

### Public API

<!-- frob:describes src/frob/strata/_audit.py::evaluate_exhaustiveness -->
<!-- frob:describes src/frob/strata/_audit.py::AuditReport -->
<!-- frob:describes src/frob/strata/_audit.py::FamilyGap -->

### CLI wiring

<!-- frob:describes src/frob/app/sys_runner.py::_run_audit -->
<!-- frob:describes src/frob/app/sys_runner.py::_print_audit_report -->

### The vuln-litmus pair

`design/litmus/audit_vuln.strata` is a deliberately-vulnerable model whose
`may "sql"` capability fires an undischarged THREAT003 obligation in both
the security (CWE-89) and quality (CWE-639) families -- refuted by `frob
sys audit` with exactly those two named gaps (tests/unit/strata/test_
litmus_audit_vuln.py, permanent CI golden). `design/litmus/audit_hardened.
strata` is its hardened twin: the SAME firing preconditions, both
discharged as assumed `NoFlow` claims named `weakness:<cwe-id>:<node-id>`
(tests/unit/strata/test_litmus_audit_hardened.py, permanent CI golden) --
a STRING-quoted claim id, the alternate surface form T-0138 added
alongside the pre-existing bare-IDENT form so a claim id can carry `:`/
`-`. The compliance family is still built as a `KernelModel` fixture
directly in tests/unit/strata/test_audit.py instead of a third `.strata`
file: a separate surface-grammar gap (no `.strata` source can author a
`subject:child`-tagged flow attr today) blocks that leg specifically. See
that test module's docstring for the full explanation.
