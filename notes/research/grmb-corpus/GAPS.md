# What the rev 2 grammar could not express (input to R2)

## Inexpressible

| Id | Gap | Seen in | Workaround used |
|---|---|---|---|
| G1 | fork/join and fire-and-forget (parallel or detached branches) | stress f05, d04 | serialize with `->`; concurrency is lost silently |
| G2 | loop over a SUCCESS outcome with a data-dependent exit (pagination, polling) | stress f06, d11 | model the loop in code, one step with `{ ok, last_page }` |
| G3 | time-bounded retry on a domain outcome | stress f07 | only ambient `restart ... within T`; domain `retry` has `max` only |
| G4 | state machines and modes (online/offline, scene lifecycle) | d06, d07 | outcomes per scenario; no state carried between scenarios |
| G5 | row-level or per-item partial failure in a batch | d08 | one outcome per step |
| G6 | prose-to-grmb authoring (renderings are read-only) | stress f16 | none |
| G7 | generic or payload-typed outcomes, free-text model output | d11 | variants only |
| G8 | cross-cutting properties (tenant isolation, RLS, hazards, role hierarchy) that are not a path | d09, d10 | `non_goal` and prose; no entity |
| G9 | preemption and priority ordering (ISR vs main loop), hard deadlines | d02, d07 | `budget` claim without ordering |
| G10 | branching code paths inside one waypoint (the chain is linear) | all impl chains | one waypoint per branch target, or an outcome map |
| G11 | delivery semantics (at-least-once, ordering) as an outcome property | d04, d03 | none |

## Syntax these mockups assumed (not defined in planning.md)

The design gives no concrete grammar for these; the corpus invented a
spelling so the files read naturally. R2/P0 must either define or reject
each:

- `actor x : timer { period 1 s; }` (timer actor with a period)
- `budget <name> <duration>;` on a system
- `non_goal name;` as a bare member
- `sorry` as a whole impl body (`impl ... sorry;`) and inline `sorry because = "..." ticket = "..."` in an arm
- `renamed_from "old"` as a step clause
- `step ... -> open { ... }` and `idempotent` after the outcome set
- `goal x as one_of { ... }` (the design says `one_of { ... }` groups; the `as` key form is a guess)
- `scenario ... { include l4; fails with { ... } }` spelling in f03
- chain waypoint kinds `isr`, `driver`, `topic`, `handler`
- `cli = "..."` realization on an impl
