---
id: T-1083
title: 'arch: abstraction-opportunity remaining single-file packages extraction (T-0393/T-1067
  remainder, 23 findings)'
state: dropped
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/
- src/frob/dup/
- src/frob/lang/
- src/frob/perf/
- src/frob/process/
- src/frob/render/
- src/frob/serve/
- src/frob/strata/
- src/frob/testing/
- src/frob/tickets/
- src/frob/vet/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). The
remainder of the 84 abstraction-opportunity findings not covered by this
pass's sibling per-package tickets (gates/**, arch/**, app/**) is spread
one-or-two-per-file across ~19 small/standalone modules, ~23 findings
total: `check/_native.py` 1, `check/_python.py` 1,
<!-- frob:waive DOC006 reason="describes the per-file finding count as measured at filing time (T-1067); dup/_pipeline.py has since been split into a package (T-1099-era), rewriting would misrepresent what was actually filed" -->`dup/_pipeline.py` 2,
`lang/__init__.py` 1, `lang/_extract.py` 1, `lang/_walk_kotlin.py` 1,
`perf/_loop_effects.py` 1, `process/parsers/cargo.py` 1,
`render/_renderer.py` 1, `serve/_tools.py` 1, `strata/_compliance.py` 1,
`strata/_export.py` 1, `strata/_selfconform.py` 1, `testing/_collect.py` 1,
`tickets/__init__.py` 3, `tickets/_journal.py` 1, `vet/_capability.py` 1,
`vet/_ecosystem.py` 1, `vet/_lockfile.py` 1.

Two of these are almost certainly detector-precision FP classes, not
genuine dup -- triage these FIRST since they may be quick T-1068-style
detector fixes rather than code changes:

- `testing/_collect.py`: `collect_python_tests`/`collect_rust_tests`/
  `collect_ts_tests`/`collect_cpp_tests` sharing `(Path) -> Result[...]`
  is textbook per-language-parity shape, but T-1068's
  `_is_language_parity_family`/`_LANGUAGE_TAGS` only recognizes the
  segments `py`/`rust`/`kt`/`ts`/`cpp` -- `python` never matches `py` as
  a whole underscore-delimited segment, so this family falls through
  uncaught. Likely fix: extend `_LANGUAGE_TAGS` (or add a synonym map --
  `python`->`py`, `typescript`->`ts`, `kotlin`->`kt`, `cplusplus`->`cpp`)
  in `src/frob/arch/_python.py`, in scope src/frob/arch/ not this
  ticket's scope -- file as its own small detector ticket instead of
  fixing it here.
- `render/_renderer.py`: `RenderWriter.heading`/`.subhead`/`.good`/
  `.warn`/`.muted` are each ALREADY documented (existing `frob:invariant`
  comments at each site) as deliberate same-name thin forwarders to the
  identically-named module-level `frob.render._elements`/`_palette`
  function -- a documented, load-bearing naming convention (the vocabulary
  namespace pattern T-0448/T-0460 established), not an accidental
  duplicate. Extracting a shared `_forward(name, fn, text)` wrapper would
  likely make this WORSE (indirection with no real dedup, since each
  forwards to a different target). Recommend accepting this as a new FP
  class and filing a small T-1068-style detector ticket (recognize a
  same-name call-through to an identically-named imported symbol as
  non-actionable) in scope src/frob/arch/, not extracting here.

The rest (`tickets/__init__.py`'s 3 groups, `vet/_capability.py`'s
4-member `walk`/`walk`/`walk`/`walk` group -- likely local nested-closure
tree-walk helpers with different captured free variables per T-1067's
sibling arch-package ticket note, worth the same "read before extracting"
caution -- and the remaining single-group files) are smaller, more
plausible genuine-duplication candidates; read each before deciding.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity, excluding gates/**, arch/**, app/**) before
starting; other tickets may land in the interim and change the count.

## Drop reason
- 2026-07-29: disposition-complete, no extraction warranted: the w20-arch pass re-measured and read every remaining in-scope abstraction-opportunity finding -- all coincidental same-signature dispatch/case-handler families, none genuine duplication (full per-family record preserved on branch w20-arch, commit a8085d7f, plus its fail-log). The two real detector-precision gaps it found are refiled as T-1181/T-1182. A feature-kind ticket structurally cannot close on a zero-code disposition (EvidenceScopeUnbound), and reclassifying kind to force a close would misrecord what happened -- drop-with-reason is the honest terminal state.