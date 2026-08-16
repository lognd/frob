## Addendum 2 (independently reproduced: `frob cycle` is vacuously green on src-layout)

Reproduced the coordinator's positive control directly, byte-identical
two-file import cycle, differing only in `src/` layout:

    frob cycle <toplevel-copy>   -> cycle (2 nodes): pkg/b.py -> pkg/a.py -> pkg/b.py
    frob cycle <srclayout-copy>  -> no cycles found

Confirms: `resolve_local_import`'s defect is not confined to `frob.graph.
callgraph`/T-2156 attribution. Every consumer of `frob.lang.extract_
imports`/`resolve_local_import` for python import-graph edges is
affected on THIS repo (src-layout) and any other src-layout project.
Grepped consumers beyond `callgraph.py`, not yet individually verified
by me with the positive-control technique (left for whoever picks up the
fix, or a fast follow-up once the primitive itself is fixed and each
consumer can be re-measured with a real known-good cycle/layering
violation as the discriminating test, not just "clean" as the outcome):

    src/frob/app/cycle_runner.py:61      frob cycle          -- CONFIRMED vacuous above
    src/frob/arch/_layering.py:144,252   layering analysis   -- not yet independently confirmed, same primitive
    src/frob/arch/_python.py:330         python arch         -- not yet independently confirmed, same primitive

Fix guidance (grammar, not path lexical): do NOT special-case the
literal string `src/`. Resolve import roots from DECLARED project
configuration (`pyproject.toml`'s `[tool.setuptools]`/`packages.find`,
or `[tool.hatch.build]`) and the importing module's own package
position (derived from `__init__.py` presence up the tree), not a
hardcoded directory name -- `lib/`, a namespace package, or a monorepo
subdirectory all reopen a lexical `src/` fix immediately.

Acceptance criteria (must all pass, including the "still works" cases --
a fix must not trade one blind spot for another):

- absolute src-layout: `frob.tickets._land` from
  `src/frob/tickets/_land_git_ops.py` resolves to `src/frob/tickets/_land.py`
- relative sibling: `._land` from the same file resolves to the same path
- relative parent: `..lang._nodes` resolves to `src/frob/lang/_nodes.py`
- REGRESSION GUARD: `scripts.fleet_status` -> `scripts/fleet_status.py`
  (the one form that resolves TODAY) must keep resolving
- two-layout cycle control: `frob cycle` reports the SAME cycle for both
  the top-level-layout and src-layout copies of the identical fixture

This also means: do NOT unblock T-2188 on a partial fix that only
handles the absolute src-layout case named in this ticket's original
title -- the relative forms and the `frob cycle`/arch blast radius must
be part of the same acceptance pass, or T-2188's own consumers (DEAD001
especially) inherit the same "reports clean because it sees nothing"
failure mode `frob cycle` has right now.
