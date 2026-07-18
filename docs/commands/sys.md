# frob sys

Strata design-model operations. Today: `frob sys plan`, the obligation ->
ticket compiler (T-0084). Later phase-5 siblings per
`docs/strata/roadmap.md` (`check`, `trace`, `capacity`, `threats`, `doc`,
`export`) are separate future tickets, not implemented here.

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

## CLI wiring

<!-- frob:describes src/frob/app/sys_runner.py::run -->
