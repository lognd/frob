---
id: T-4301
title: expose dev-version-bump toggle/ack via a CLI surface (frob release status)
state: done
kind: feature
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/_cli.py
- tests/test_release.py
- src/frob/release/__init__.py
scope_breadth_ack: true
scope_breadth_ack_reason: SCOPE002's doc/test closure over docs/modules/release.md
  and tests/test_release.py both fan out into the WHOLE release subsystem (release/__init__.py,
  _fragments.py, _publish.py) plus gates/__init__.py's REL001/REL002 gates via that
  same shared doc file -- pulling all of that into a single CLI-wiring ticket's scope
  is out of proportion (same posture T-1010's own SCOPE002/COV001 ack took for docs/modules/gates.md's
  identical fan-out, see tickets/archive/T-1881/evidence/stage1-frob-check.json).
  T-4301 only adds a new frob release status verb in src/frob/release/_cli.py plus
  its own tests/docs entries; it does not touch the pre-existing release/publish/fragments/gates
  surface these closure edges point at.
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/release.md
  reason: 'T-4301: status verb''s own docs anchor and unit tests live in these shared
    files, not just src/frob/release/_cli.py'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_release.py
  reason: 'T-4301: status verb''s own docs anchor and unit tests live in these shared
    files, not just src/frob/release/_cli.py'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/release/__init__.py
  reason: 'T-4301: docs/modules/release.md''s scope closure requires every symbol
    that shared doc file already describes (pre-existing anchors, not touched by this
    ticket) to be in scope once the file itself is added for the new status-verb section'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/release/_fragments.py
  reason: 'T-4301: docs/modules/release.md''s scope closure requires every symbol
    that shared doc file already describes (pre-existing anchors, not touched by this
    ticket) to be in scope once the file itself is added for the new status-verb section'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/release/_publish.py
  reason: 'T-4301: docs/modules/release.md''s scope closure requires every symbol
    that shared doc file already describes (pre-existing anchors, not touched by this
    ticket) to be in scope once the file itself is added for the new status-verb section'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-4301: docs/modules/release.md''s scope closure requires every symbol
    that shared doc file already describes (pre-existing anchors, not touched by this
    ticket) to be in scope once the file itself is added for the new status-verb section'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: 'T-4301: back out of a doc-closure cascade -- docs/modules/release.md already
    describes the whole release subsystem including gates/__init__.py''s RELxxx gates,
    pulling in unrelated docs/modules/gates.md and perf.md closures; dropping the
    new doc section instead of widening scope repo-wide for a CLI-wiring ticket'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/release/__init__.py
  reason: 'T-4301: back out of a doc-closure cascade -- docs/modules/release.md already
    describes the whole release subsystem including gates/__init__.py''s RELxxx gates,
    pulling in unrelated docs/modules/gates.md and perf.md closures; dropping the
    new doc section instead of widening scope repo-wide for a CLI-wiring ticket'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/release/_fragments.py
  reason: 'T-4301: back out of a doc-closure cascade -- docs/modules/release.md already
    describes the whole release subsystem including gates/__init__.py''s RELxxx gates,
    pulling in unrelated docs/modules/gates.md and perf.md closures; dropping the
    new doc section instead of widening scope repo-wide for a CLI-wiring ticket'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/release/_publish.py
  reason: 'T-4301: back out of a doc-closure cascade -- docs/modules/release.md already
    describes the whole release subsystem including gates/__init__.py''s RELxxx gates,
    pulling in unrelated docs/modules/gates.md and perf.md closures; dropping the
    new doc section instead of widening scope repo-wide for a CLI-wiring ticket'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/release.md
  reason: 'T-4301: back out of a doc-closure cascade -- docs/modules/release.md already
    describes the whole release subsystem including gates/__init__.py''s RELxxx gates,
    pulling in unrelated docs/modules/gates.md and perf.md closures; dropping the
    new doc section instead of widening scope repo-wide for a CLI-wiring ticket'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/test_release.py
  reason: 'T-4301: testing scope-closure blast radius before deciding where new tests
    live'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_release.py
  reason: 'T-4301: restore -- required since src/frob/release/_cli.py::run_release_publish_command''s
    PRE-EXISTING frob:tests binding to this file is unavoidable once _cli.py is in
    scope at all'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/release/__init__.py
  reason: 'T-4301: closing this ticket requires re-pointing/resolving the two WIRE001
    waivers in dev_version_bump_enabled/dev_version_major_ack that cite T-4301 as
    their follow_up -- now wired, so the waivers are satisfied and must be removed'
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'T-4301: waive SCOPE002''s doc/test closure fan-out into the whole release+gates
    subsystem instead of widening scope repo-wide'
  actor: logan
  at: '2026-09-08'
  old_length: 466
  new_length: 1547
evidence:
- tests/test_release.py::TestRunReleaseStatusCommand::test_reports_bump_required_when_gate_refuses
- tests/test_release.py::TestRunReleaseStatusCommand::test_reports_ok_and_dev_bump_toggle_state
- tests/test_release.py::TestAddReleaseStatusParser::test_registers_release_status
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up from T-4184: frob.release.dev_version_bump_enabled/dev_version_major_ack are public read-only introspection functions with no in-repo CLI caller yet (WIRE001, waived on both pending this ticket). Wire them into a real consumer -- e.g. a 'frob release status' subcommand printing whether the per-land dev-version bump is on and what major series is acknowledged -- so the public API this ticket added has an actual production caller, not just its own tests.


## SCOPE002 waiver (T-4301)

# frob:waive SCOPE002 reason="docs/modules/release.md and tests/test_release.py are \
large shared release-module files whose existing frob:doc/frob:tests closure fans out \
into the WHOLE release subsystem (src/frob/release/__init__.py, _fragments.py, \
_publish.py) plus src/frob/gates/__init__.py's REL001/REL002 gates (and, transitively, \
docs/modules/gates.md/perf.md via THAT file's own closure) -- pulling all of that into \
a single CLI-wiring ticket's scope is out of proportion. T-4301 only adds a new `frob \
release status` verb (add_release_status_parser/run_release_status_command) in \
src/frob/release/_cli.py plus its own two test classes in tests/test_release.py; it does \
not touch the pre-existing publish/release/fragments/gates surface these closure edges \
point at. Same posture T-1010's own SCOPE002/COV001 waiver took for docs/modules/gates.md's \
identical fan-out (see tickets/archive/T-1881/evidence/stage1-frob-check.json) and T-4298's \
own SCOPE002 waiver for src/frob/gates/__init__.py's shared-registry closure."