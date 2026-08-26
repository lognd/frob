---
id: T-2989
title: Rename frob.yaml_io to frob.yamlio for io-seam naming consistency (via frob
  refactor, not hand-edits)
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/yaml_io.py
- src/frob/yamlio.py
- src/frob/__init__.py
- src/frob/gates/_fmt_directives.py
- src/frob/gates/decisions.py
- src/frob/gates/invariants.py
- src/frob/registry/_models.py
- src/frob/tickets/_store.py
- src/frob/vet/_lockfile.py
- src/frob/derived_state.py
- tests/unit/perf/test_hotpath_smells.py
- tests/unit/test_ticket_store.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/yaml_io.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/yamlio.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/__init__.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_fmt_directives.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/decisions.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/invariants.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/registry/_models.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/_store.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/vet/_lockfile.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/derived_state.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/perf/test_hotpath_smells.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: rename frob.yaml_io -> frob.yamlio via frob refactor move-module; 21 references
    across 11 files plus new module path
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`src/frob/yaml_io.py` is the only io-seam module carrying an underscore. Its
siblings are `src/frob/gitio.py` and `src/frob/tomlio.py`. The in-flight
GitHub/CI seam (T-2983) has been redirected to land as `ghio` for the same
reason, so `yaml_io` would be the last holdout of a spelling actively being
removed.

Rename `frob.yaml_io` -> `frob.yamlio`.

MEASURED SCOPE:
- `src/frob/yaml_io.py` is 73 lines.
- Public surface is a SINGLE symbol: `fast_yaml_loader`.
- Module-private: `_coverage_tracer_active`, `__all__`.
- References: 21 across 11 files (src/, tests/, docs/).

METHOD -- USE THE TOOL, DO NOT HAND-EDIT. The owner asked specifically that this
go through `frob refactor` so that import rewriting is done by the machinery
rather than by hand. `frob refactor move` takes `MODULE:QUALNAME` pairs and
rewrites all references:

    frob refactor move frob.yaml_io:fast_yaml_loader frob.yamlio:fast_yaml_loader

Then deal with the residue deliberately:
- `_coverage_tracer_active` is module-private and presumably supports
  `fast_yaml_loader`. Determine whether the move carried it; if not, move or
  relocate it so the new module is self-contained and the old one is genuinely
  empty.
- Once `yaml_io.py` holds nothing live, delete it. Do not leave a re-export shim
  -- this is an internal seam with 21 in-repo references and no external
  consumers, so a shim would just be a second name for the thing we are renaming
  to eliminate a second name.
- `__all__` must reflect the new module.

VERIFY, do not assume the tool got everything:
- `git grep -c yaml_io` over src/, tests/, docs/ must be ZERO afterwards
  (currently 21). A stale reference in a docstring or a doc page still counts --
  the point of the rename is that one spelling exists.
- The refactor machinery runs a `frob check --delta` post-condition and a
  pytest collect; let both run rather than passing `--skip-check-delta`.
- Confirm the import actually works at runtime, not merely that text was
  rewritten: exercise `fast_yaml_loader` through a real call path.

ACCEPTANCE
- `frob.yamlio` exists, `frob.yaml_io` does not, and no shim remains.
- `git grep -c "yaml_io"` across src/, tests/, docs/ returns 0.
- The rename was performed by `frob refactor move`, not by hand-editing imports
  -- state in the Done report which command(s) you ran.
- Existing tests covering `fast_yaml_loader` pass unchanged.

NOTE FOR WHOEVER TAKES THIS: if `frob refactor move` cannot express a whole-module
rename cleanly (it is symbol-scoped by design), say so explicitly rather than
silently falling back to manual edits. That is a real finding about the refactor
tooling's coverage and is worth its own ticket -- a module rename is a common
operation and the tool arguably should support it directly.
