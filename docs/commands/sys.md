# frob sys

Strata design-model operations. Today: `frob sys plan`, the obligation ->
ticket compiler (T-0084), and `frob sys doc`, the threat-catalog audit
matrix (T-0085). Later phase-5 siblings per `docs/strata/roadmap.md`
(`check`, `trace`, `capacity`, `export`) are separate future tickets, not
implemented here.

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

## Usage

```bash
frob sys plan                 # dry-run: print the would-be ticket tree
frob sys plan --apply         # write the tickets to tickets.md
frob sys plan /path/to/repo   # plan a different repo root
```

Dry-run is the default deliberately -- a plan is a proposal, not a
side-effecting command, until `--apply` says otherwise.

## Idempotency

Every planned ticket's body carries exactly one `sys-plan:<construct-
qualname>:<obligation-kind>` marker line. `frob sys plan` diffs the
freshly compiled marker set against every marker already present in some
ticket's body (open or closed) before writing anything: re-running
against an unchanged model creates nothing new, and re-running after a
model change creates only the delta (the new/changed markers). A ticket
is never re-created after being closed, since the marker matches
regardless of ticket state -- closing a sys-plan ticket is the discharge
signal, not a re-open trigger.

## Public API

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

## Public API

<!-- frob:describes src/frob/strata/_sysdoc.py::render_audit_matrix -->
<!-- frob:describes src/frob/strata/_sysdoc.py::audit_claim -->
<!-- frob:describes src/frob/strata/_sysdoc.py::ClaimAuditResult -->
<!-- frob:describes src/frob/strata/_sysdoc.py::merge_models -->

## CLI wiring

<!-- frob:describes src/frob/app/sys_runner.py::run -->
<!-- frob:describes src/frob/app/sys_runner.py::_run_doc -->
