---
id: T-2231
title: 'Break gates/lang/graph import cycle: _docblocks<->_docblocks_refs split plus
  lang<->graph.cache lazy-break not recognized by static cycle check'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: T-2202
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_docblocks_refs.py
- src/frob/gates/_docblocks.py
- src/frob/lang/_support.py
- src/frob/graph/cache.py
- src/frob/lang/__init__.py
- src/frob/graph/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given current main, when 'uv run frob check --only cycle' runs, then this
    cluster (_docblocks_refs.py -> _docblocks.py -> lang/_support.py -> graph/cache.py
    -> lang/__init__.py -> graph/_models.py -> _docblocks_refs.py) no longer appears
    in the FAIL output. This test MUST currently fail (the cluster is in today's output).
  evidence: []
- text: 'MUST-STILL-PASS CONTROL: after the fix, ''uv run frob check --only cycle''
    still reports the dup/_pipeline cluster, the vet warning cluster, and the tickets/app/serve/verify
    mega-cluster (or their post-fix equivalents) -- a fix that makes frob-cycle report
    fewer TOTAL clusters than it found before this leaf''s own fix is a narrowing
    of the detector, not a fix, and must be rejected.'
  evidence: []
- text: 'DESIGN NOTE (not mechanical-only): this cluster merges two distinct issues
    and needs a design decision before implementation. (1) gates/_docblocks.py and
    gates/_docblocks_refs.py mutually import each other (docblocks.py line ~773+ imports
    names back from _docblocks_refs.py, which at line 16 imports from _docblocks.py)
    -- likely a same-package split-file cycle, fixable by extracting the shared symbols
    _docblocks_refs.py and _docblocks.py both need into a third gates-local module.
    (2) graph/_models.py imports frob.lang (for SymbolKind) and frob.lang/__init__.py
    already contains an explicit, DOCUMENTED lazy-import workaround (see its own comment
    at line ~704-708: ''to dodge the same frob.lang/frob.graph circular-import trap
    frob.graph.cache imports frob.lang at module level, so this module imports it
    lazily'') for exactly this frob.lang<->frob.graph.cache circularity -- the static
    cycle checker does not distinguish module-level from function-scope (lazy) imports,
    so it flags an already-intentionally-broken runtime cycle as if it were live.
    OPEN QUESTION for the design: should frob-cycle be taught to treat a function-scope-only
    import as a non-cycle-forming edge (matching Python''s actual runtime semantics),
    or should the lang/graph dependency be inverted for real (e.g. move SymbolKind
    to a leaf module both sides depend on) so the structural cycle is gone even from
    lazy-import readers? Do not silently narrow the cycle detector to make this vanish
    -- if the checker-side option is chosen it needs its own ticket/discussion, not
    a quiet loosening.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Leaf of T-2202 (epic). Measured directly from 'uv run frob check --only cycle' on 2026-08-16, which now differs from T-2202's originally recorded cluster (T-2202 described a 5-file cluster ending at graph/cache.py; today's is 6 files and also includes graph/_models.py). The growth is attributable to T-2211 (landed after T-2202 was filed), which fixed resolve_local_import to stop dropping imported names for the 'from X import submodule' idiom -- previously-invisible edges through that idiom are now real graph edges. Not a regression; do not revert anything.