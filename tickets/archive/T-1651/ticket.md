---
id: T-1651
title: 'LARGE001 remainder: 51 oversized files after T-1646''s one-file split'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- design/frob.strata
- tests/**
- docs/modules/gates.md
- src/frob/app/config.py
- src/frob/gates/_waive.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: 'T-1651: narrowing broad src/frob/** scope to the specific LARGE001 files
    this round actually touches (waivers on config.py, _waive.py, _models.py); tests/**
    and docs/modules/gates.md remain for future split work in this same series

    '
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1651: narrowing broad src/frob/** scope to the specific LARGE001 files
    this round actually touches (waivers on config.py, _waive.py, _models.py); tests/**
    and docs/modules/gates.md remain for future split work in this same series

    '
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1651: narrowing broad src/frob/** scope to the specific LARGE001 files
    this round actually touches (waivers on config.py, _waive.py, _models.py); tests/**
    and docs/modules/gates.md remain for future split work in this same series

    '
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
- tests/test_arch_gate.py::TestArchGateLargeFile::test_test_file_exempt_from_large001
- tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk
designated_repro_test: null
threat: null
component: null
---
T-1646 split one file this round: src/frob/gates/_fix_engine.py (1940
lines, the single highest edit-frequency LARGE001 file, 34 edits over the
last 400 commits) into four modules along the seam the file's own
handler set already carried by convention (this repo already has
_fix_engine_tier_b.py/_fix_engine_tier_c.py as precedent for exactly this
kind of tiered handler-family split):

- _fix_engine.py (571 lines): graph-driven handlers (DOC007, DOC002,
  INV006-carry, TICK002) plus the shared infra binding every handler
  together (TIER_A_HANDLERS, apply_tier_a_fixes).
- _fix_engine_shared.py (135 lines): FixApplied + the crash-safe
  write/manifest infra every handler family needs (split out to avoid a
  circular import between the other two).
- _fix_engine_text.py (688 lines): diagnostic-LINE handlers (FMT001,
  SUPPRESS001, E501) that rewrite the one source line a Violation names.
- _fix_engine_sync.py (684 lines): derived-artifact-SYNC handlers
  (REG010, REL002, SYS104, SYS100, COV002, WAIVE004) that resync a whole
  generated artifact.

Result: gate:LARGE 55 -> 54 (one fewer file over the 800-line frob.toml
threshold; the other 3 new files all land under it). design/frob.strata's
gates node code= globs were updated for the split (both fs.read/fs.write
lists) and `frob sys sync-interface` reports 0 drift. All frob:describes
and frob:tests anchors that named the moved symbols' old file were moved
to their real new location (docs/modules/gates.md, tests/test_gates.py,
tests/test_gates_fix_engine.py) -- scope was widened via `frob ticket
scope --add docs/modules/gates.md` for the doc-anchor half of that.

51 files remain, named in T-1646's own body (src/frob/gates/__init__.py
7627 lines/63 edits highest priority by edit frequency, src/frob/tickets/
_land.py 2696/29, src/frob/tickets/_store.py 2230/25, src/frob/strata/
_selfconform.py 1925/20, src/frob/gates/_fix_engine_sync.py itself now at
684 lines under threshold so NOT part of this remainder, plus ~47 more --
see T-1646's own ranked list, still valid, ranked by
`git log --format=%H --name-only -400`). Each still needs the same
judgement call T-1646's own body asks for: find the real seam or waive
with a specific reason, never split purely to clear the line count.

Filed per T-1646's own instruction ("If you cannot finish all 52 --
expected -- fix what you can and FILE A FOLLOW-UP TICKET for the
remainder") and per this repo's own T-1420/T-1204 incident history
(closing a partially-worked LARGE001 ticket without filing the
remainder silently dropped it from the queue twice already).