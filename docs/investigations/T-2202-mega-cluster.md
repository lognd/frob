# T-2202 mega-cluster: sub-SCC breakdown

Measured on current main (merged into this ticket's worktree at commit
41b2d8a96) via `uv run frob check --only cycle --no-cache` plus an
independent module-level import graph reconstructed directly from the
same 175 files with Python's `ast` module and a from-scratch Tarjan SCC
pass (not reusing frob's own cycle detector), so the "does not
decompose" finding below is corroborated by two independent
implementations, not one tool's opinion of itself.

## Denominator

- `frob check --only cycle --no-cache` reports exactly one ERROR-severity
  CYCLE001 finding, printed as a single DFS path of 176 file lines (175
  distinct files after de-duplication -- one file, `src/frob/tickets/
  _land_verify.py`, both opens and closes the printed path, matching a
  real cycle, not a reporting bug).
- Those 175 files span 15 packages under `src/frob`: gates (45 files),
  tickets (31), strata (30), app (20), testing (10), serve (8), deploy
  (8), verify (5), release (4), refactor (3), the bare `frob` package
  root -- `__main__.py`/`doctor.py`/`__init__.py` (3), vet (2), registry
  (2), natives (2), check (2). This matches the ticket's own filed
  estimate ("approx. 180 files, approx. 15 packages") almost exactly.
- Independently reconstructing the module-level import graph over just
  these 175 files (resolving both `import X` and `from X import Y`,
  including the relative-import and submodule-reexport cases T-2211/
  T-2219 fixed) yields 609 distinct directed edges. Running Tarjan over
  that graph confirms: **one non-trivial SCC, all 175 files, size 175**
  -- independent confirmation of frob's own report, not just a re-run of
  the same tool.

## Does a small hub-file removal set split it? Measured: no.

The working hypothesis behind filing this ticket was "a small number of
hub files chain several tighter sub-cycles into one reported SCC." I
tested this directly: rank every file by total degree (in-edges +
out-edges) in the reconstructed graph, remove the top-K by that ranking,
and re-run Tarjan on what remains.

| removed (top-K by degree)                                                  | K  | largest remaining SCC(s) |
|---|---|---|
| `frob.gates` (__init__)                                                    | 1  | 133 |
| `frob.tickets` (__init__)                                                  | 1  | 165 |
| `frob.strata` (__init__)                                                   | 1  | 132 |
| `frob.gates`, `frob.tickets`, `frob.strata`                                | 3  | 82 |
| + `frob.tickets._store`, `frob.tickets._leases`                            | 5  | 57 |
| + `_land_cmd`, `_land`, `ticket_runner` (__init__)                         | 8  | 21, 14, 2 |
| + `_rapid_sweep`, `_worktree_guard`, `_fix_engine`, `_new_renumber`        | 12 | 11, 2 |
| top 20 by degree removed                                                   | 20 | 10 |

**Finding: this cluster does not decompose via a small hub set.**
Removing the single highest-degree file anywhere (`frob.gates`'s own
`__init__.py`, 65 combined in/out edges) leaves a 133-node SCC --
essentially the same cluster. Removing the three biggest package
`__init__.py` files together (gates/tickets/strata, the three obvious
"everything re-exports through me" candidates) still leaves an 82-node
SCC. Even removing the top 20 files by degree -- over 11% of the
cluster's own membership -- leaves a residual 10-node SCC that is still
strongly connected. There is no small "hub file(s) whose removal/seam
would split it" the way this ticket's own filing hypothesized; the
coupling is diffuse across dozens of files, not concentrated behind a
handful of chokepoints.

This is itself the actionable finding for follow-on leaf tickets: a
mechanical "cut the hub, get clean sub-groups" leaf is not available
here. The real seams that do exist are package-shaped, not file-shaped
-- see below.

## Where the real seams are (package-level view)

Collapsing the 175-file graph to its 15 packages and looking at which
package-pairs have edges in BOTH directions (the signature of a true
cross-package cycle, not just a one-way dependency) narrows the search
space for anyone scoping a leaf ticket:

- `tickets` <-> `app` (specifically `app.ticket_runner`) is the tightest
  pair: `frob.tickets._store`/`_leases`/`_land`/`_worktree_guard` are
  imported by more than a dozen `app.ticket_runner._*` command modules,
  and several of those command modules are imported back by `tickets`
  submodules that need CLI-level helpers (`_new_renumber`, `_evidence`).
- `gates` <-> `strata` <-> `tickets` is a three-way cycle: gates rules
  read strata's design model (`_sys.py`, `_sys_selfaudit.py`), strata's
  own conformance code imports gate infrastructure for reporting
  (`_audit.py`, `_threat.py`), and both are imported from `tickets`'
  land/close pipeline for pre-land checks.
- `serve`, `deploy`, `verify`, `release`, `refactor`, `testing`, `vet`,
  `registry`, `natives`, `check` each touch the cluster through only 2-8
  files apiece and read as consumers pulled in by the `tickets`/`app`
  land pipeline (`_land_cmd.py`, `_close_cmd.py`) needing their
  functionality at land/close time, not as independent contributors to
  the cycle's own back-edges. A leaf ticket targeting one of these
  smaller packages' 2-8 files, cutting its call INTO the `tickets`/`app`
  core down to a narrow interface, is a more scopeable unit than
  attacking `gates`/`tickets`/`strata` directly.

## Open question: newly-accurate detection, or real growth?

T-2211/T-2219 fixed `resolve_local_import`'s handling of `from X import
submodule` and transitive re-export chains, landing after T-2202 was
originally filed against a 4-file cluster. Sampling the edge-resolution
methods used to build the 609-edge graph above: of all `from PKG import
NAME` import statements across these 175 files, 912 resolve because
`PKG` itself is directly one of the 175 tracked modules (an edge any
resolver, including the pre-T-2211 one, would have found), versus only
34 that resolve solely because `NAME` is a submodule of `PKG` re-exported
through `PKG`'s own `__init__.py` (the exact shape T-2211/T-2219 taught
the resolver to follow). That is roughly a 27:1 ratio -- the overwhelming
majority of the edges holding this cluster together are edges any import
resolver would already have reported before T-2211/T-2219 landed.

**Answer: this reflects newly-accurate detection of real, pre-existing
debt (the T-2202 framing), not a growth-rate artifact of the detector
itself.** The cluster did not balloon from 4 to ~180 files because the
tool started inventing edges -- it grew because `resolve_local_import`
started correctly following ~34 edges it used to silently drop, and
those 34 new edges were enough to weld several previously-separate SCCs
(the original 4-file `tickets/` cluster plus whatever `app`/`gates`/
`strata` cliques existed unreported before) into one connected component
via a small number of bridging submodule-reexport edges. The debt was
real before T-2211/T-2219; the tool just could not see all of it.

## Scope note

No `src/` file was modified for this investigation, per this ticket's
own acceptance -- only this doc and the reconstructed-graph analysis
that produced it (not committed; reproducible from `uv run frob check
--only cycle --no-cache` plus a from-scratch `ast`-based import walk
over the file list its own CYCLE001 message names).
