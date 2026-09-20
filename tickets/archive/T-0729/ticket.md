---
id: T-0729
title: 'sys audit red on main: _srp.py classifier string tables read as graphlang
  capability observations (4x SYS100)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: critical
parent: T-0330
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_srp.py
- design/frob.strata
- src/frob/strata/**
- src/frob/vet/_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability.py
  reason: the established self-pattern-path exemption mechanism (T-0201/T-0253) that
    classifier corpora use to escape SYS100 lives in this file (_SELF_PATTERN_SUFFIXES/is_self_pattern_path);
    mirroring it for _srp.py's tables requires adding _srp.py's own suffix entry here
  actor: logan
  at: '2026-07-22'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 837
  new_length: 2004
evidence:
- tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_io_compute_and_formatting_together_trigger
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy
designated_repro_test: null
acceptance:
- text: GIVEN main after the fix WHEN frob sys audit runs THEN zero SYS100 gaps and
    no dishonest may declarations were added
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0616's landed _srp.py carries curated classifier tables (_IO_MODULE_PREFIXES: socket., subprocess., requests., urllib. ...) that the capability scanner -- which keys on string-literal content by design, for evasion detection -- reads as live net/exec/fetch_url observations on the graphlang node: frob sys audit on main now reports 4 SYS100 gaps (zero-errors violation). These strings are classifier DATA, not capability usage. Disposition honestly at the correct layer: per-observation waiver with reason (classifier corpus, not usage -- cite the file/lines) via the established SYS waive channel, OR if the scanner has a data-table exemption convention, use it; declaring may net/exec on graphlang would be DISHONEST (the node does no such thing). Found by T-0724's rework (its T-draft-890e0667 duplicates this -- reconcile at land).

T-4718 sweep (condensed from src/frob/vet/_capability_scan.py:188-201,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

    # T-0729: `frob.arch._srp`'s ARCH103 mixed-concern check stores its
    # I/O-classifier signals (`_IO_MODULE_PREFIXES`: `socket.`,
    # `subprocess.`, `requests.`, `urllib.`, ...) as literal string data too
    # -- the exact same self-match class as the two `_capability_registry`/
    # `_cve_fingerprint` entries above: the scanner (by design, for evasion
    # detection) keys on string-literal CONTENT, so a classifier table that
    # merely *names* `socket.`/`subprocess.`/etc. as data reads as live
    # net/exec/fetch_url capability USAGE on the `graphlang` node, which is
    # dishonest -- `_srp.py` does no such I/O itself (module docstring: it
    # only imports `frob.arch._models`/`frob.arch._normalized`). Declaring
    # `may net`/`may exec` on `graphlang` to silence this would be an
    # equally dishonest fix in the other direction, so this file is excluded
    # from self-conformance's capability scan the same way, not given a
    # capability it does not have.