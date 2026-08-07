---
id: T-0897
title: RENDER001/PII010/SEC-CVE-FINGERPRINT-001 each run a private silent-skip-on-unparseable
  file read outside PARSE001
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_render_lint.py
- src/frob/gates/_pii_structural.py
- src/frob/gates/_cve_fingerprint_scan.py
- tests/test_gates.py
- tests/unit/strata/test_cve_fingerprint_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'T-0897''s fix needs a real, passing regression test per touched gate

    (render_lint_gate/pii_structural_gate/cve_fingerprint_scan_gate) proving

    the new PARSE001-on-unparseable-file behavior, per frob:tests discipline

    (a frob:tests directive must resolve against a real collected node id).

    T-0898 (queued, same origin) tracks the BROADER regression-test sweep

    across both gates; this narrow addition only covers the exact fix landed

    here so T-0897 can close with real evidence, not a promise.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/unit/strata/test_cve_fingerprint_scan.py
  reason: 'cve_fingerprint_scan_gate''s real test home is tests/unit/strata/

    test_cve_fingerprint_scan.py (its own frob:tests directives all point

    there, not tests/test_gates.py) -- the new PARSE001-on-unreadable-file

    regression test for this gate belongs alongside its siblings, matching

    existing test-location convention rather than introducing a second home.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/fixtures/lang/broken.py
  reason: 'The fix correctly makes pii_structural_gate''s now-loud PARSE001 fire on

    this repo''s own tests/fixtures/lang/broken.py (a deliberately syntax-

    broken fixture used by tests/test_lang.py, previously invisible to

    PII010/SEC110''s private silent-skip). It needs the standard

    frob:waive PARSE001 escape hatch the fix itself documents, same as any

    other known, intentionally-unparseable fixture -- not a code change to

    the fixture''s actual test content.

    '
  actor: logan
  at: '2026-07-26'
- op: remove
  glob: tests/fixtures/lang/broken.py
  reason: 'Reverted the fixture-file waiver approach: frob.toml''s own [graph].exclude

    already carves tests/fixtures/** out of frob''s obligation surface, so the

    3 gates now consult frob.excludes.is_excluded directly instead of needing

    a per-fixture frob:waive PARSE001 comment. No edit to this fixture needed.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_python_file_fires_parse001
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_file_under_graph_exclude_is_silent
- tests/unit/strata/test_cve_fingerprint_scan.py::TestGate::test_undecodable_file_fires_parse001
- tests/unit/strata/test_cve_fingerprint_scan.py::TestGate::test_undecodable_file_under_graph_exclude_is_silent
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2).

At least three gates run their OWN private per-file read+parse, entirely
independent of `frob.lang.parse_file`'s centrally-tracked pipeline (the
one `snapshot.parse_failures`/PARSE001, T-0558, actually covers) -- and
each silently skips a file that fails to read/parse, with only a DEBUG log
line, no Violation of any kind:

- `render_lint_gate` (src/frob/gates/_render_lint.py:220-224):
  `except (OSError, UnicodeDecodeError, SyntaxError): skip` around its own
  `ast.parse(text, filename=rel_path)` call.
- `pii_structural_gate` (src/frob/gates/_pii_structural.py:1861-1865): the
  identical `except (OSError, UnicodeDecodeError, SyntaxError): skip`
  shape around its own `ast.parse` call, for PII010/SEC110.
- `cve_fingerprint_scan_gate` (src/frob/gates/_cve_fingerprint_scan.py:183-187):
  `except (OSError, UnicodeDecodeError): skip` around its plain text read
  (no parse, but the same silent-skip shape) for SEC-CVE-FINGERPRINT-001.

Net effect: a Python file with a syntax error (or bad encoding) is
invisible to RENDER001 (a bare-print-bypassing-Renderer check) and to
PII010/SEC110 (structural PII/secret-shape detection) -- exactly the two
gate families where "this file's content was never actually inspected"
matters most from a security-review standpoint -- with zero surfaced
signal that the skip happened at all, unlike the general PARSE001
mechanism T-0558 built specifically to make this class loud for the
`frob.lang`-routed gates.

Fix direction: route these three gates' file reads through the shared
`frob.lang.parse_file` (or at minimum consult
`frob.lang.partial_parse_files()`/`snapshot.parse_failures`) instead of a
private `ast.parse`/read call with its own silent except, so a single
PARSE001-shaped signal covers every gate that needs a parseable file
rather than each gate independently deciding to stay silent on failure.