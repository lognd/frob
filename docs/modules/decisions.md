# frob decision records (ADR)

One sentence: architecture decisions live as tracked `decisions/AD-###.md`
records, code that implements one anchors it with `frob:decision AD-###`,
and the DEC gates keep the "why" from rotting away from the code -- an
accepted decision must be anchored, and a decision reference must resolve.

<!-- frob:invariant INV-010 -->

## The record

`decisions/AD-001.md`:

```markdown
---
id: AD-001
title: Source of truth is tracked text, caches are derived
status: accepted          # proposed | accepted | superseded | deprecated
superseded_by: null       # AD-### when status is superseded
---

## Context
...

## Decision
...

## Consequences
...
```

## Data models

<!-- frob:describes src/frob/gates/decisions.py::_DecisionStatus -->
<!-- frob:describes src/frob/gates/decisions.py::Decision -->
<!-- frob:describes src/frob/gates/decisions.py::DecisionError -->

- `DecisionStatus` -- the lifecycle state of an ADR (`proposed` |
  `accepted` | `superseded` | `deprecated`); only `accepted` carries the
  DEC002 anchoring obligation.
- `Decision` -- one architecture decision record parsed from a
  `decisions/AD-###.md` file's YAML frontmatter.
- `DecisionError` -- fallible outcomes of loading decision records
  (malformed frontmatter, duplicate id, bad id shape).

## Anchoring in code

<!-- frob:describes src/frob/gates/decisions.py::load_decisions -->
<!-- frob:describes src/frob/gates/decisions.py::decisions_dir -->
<!-- frob:describes src/frob/gates/decisions.py::decision_gate -->

- `decisions_dir` -- the tracked `decisions/` directory holding
  `AD-###.md` records, under a given repo root.
- `load_decisions` -- parses every `decisions/AD-###.md` record; any
  malformation is a hard `Err` (the record set is a contract surface,
  like the ticket queue).
- `decision_gate` -- the pure DEC001/DEC002 comparison between loaded
  decisions and the graph snapshot's `frob:decision` edges.

A comment directive links the implementing symbol to the record:

```python
# frob:decision AD-001
def load_lock(path): ...
```

## The DEC gates

<!-- frob:describes src/frob/gates/__init__.py::decisions_gate -->

Runs inside `frob check` (and `frob check --only decisions`) whenever a
`decisions/` directory exists (opt-in by convention):

| Rule | Fails when |
|---|---|
| DEC000 | a decision record is malformed (hard-fail, like the ticket queue) |
| DEC001 | a `frob:decision AD-###` edge points at a record that does not exist |
| DEC002 | an `accepted` decision has no `frob:decision` anchor in code |

`proposed`/`superseded`/`deprecated` decisions are not required to be
anchored -- only `accepted` ones carry the obligation, so a decision can be
recorded before it is implemented and retired without churn.

## Design notes

- **Same loop as invariants.** DEC002 mirrors INV002: a claim (the decision)
  must be tied to the code that embodies it, verified statically.
- **Records are tracked text; the anchor graph is derived.** The decision
  log lives in git and reviews like code.
- **Opt-in.** No `decisions/` directory means no obligation.
