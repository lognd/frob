---
id: T-2719
title: 'RENDER001: add directory/file exemptions for standalone no-frob-import scripts'
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_render_lint.py
- tests/test_gates.py
- docs/modules/render.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/render.md
  reason: AFFECT001 requires touching this doc alongside render_lint_gate's changed
    docstring/exemption-scope description; the doc must be updated to describe the
    widened scan + exemption prefixes
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_gates.py::TestRenderLintGate::test_bare_print_fires
- tests/test_gates.py::TestRenderLintGate::test_render_package_exempt
- tests/test_gates.py::TestRenderLintGate::test_stderr_directed_print_is_silent
- tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001
- tests/test_gates.py::TestRenderLintGate::test_claude_hooks_dir_exempt
- tests/test_gates.py::TestRenderLintGate::test_fleet_status_file_exempt
- tests/test_gates.py::TestRenderLintGate::test_exemption_is_file_scoped_not_dir_scoped
- tests/test_gates.py::TestRenderLintGate::test_scan_now_covers_hooks_and_fleet_status
designated_repro_test: tests/test_gates.py::TestRenderLintGate::test_scan_now_covers_hooks_and_fleet_status
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed while working T-1614's periodic waive-audit pass (scan batch
watermark-commit=None, catchup window items 7,8,9,12,31,57-62).

RENDER001 currently exempts only src/frob/render/ (_EXEMPT_PREFIX in
src/frob/gates/_render_lint.py). At least 11 individual frob:waive
RENDER001 directives across 6 files (5 in .claude/hooks/*.py:
frob-timeout-guard.py x2, pending-background-guard.py, root-cleanliness-
detector.py, root-write-guard.py; 6 in scripts/fleet_status.py) all carry
the SAME reason: these are standalone scripts that deliberately never
import frob.* (hooks must survive without a built venv/native
extensions; fleet_status.py is a diagnostic script with the identical
constraint), so stdout IS their contract and RENDER001's frob.render
Renderer requirement structurally cannot apply.

Every individual waiver is honest and specific (verified during T-1614's
audit pass -- none is a cop-out), but this is exactly the case T-1614's
own rubric names: "a waiver on a rule that structurally cannot fire...
is noise, not an exception, and belongs in that rule's exemption list
instead." New print() calls in these same files will keep needing new
per-line waivers forever under the current design.

Proposed fix: extend _render_lint.py's exemption mechanism (currently a
single _EXEMPT_PREFIX string) to a small set of exempt prefixes/paths
covering .claude/hooks/ and scripts/fleet_status.py, then remove the now-
redundant per-line frob:waive RENDER001 directives in those files as a
follow-up once the gate change lands (do NOT remove the waivers before
the gate exemption exists -- that would just make them start failing).
Add/adjust a test_gates.py case proving the new exemption paths are
skipped, mirroring test_render_package_exempt.