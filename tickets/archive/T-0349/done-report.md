## Done report

Changed:
- src/frob/gates/_pii_structural.py: new PII011 rule (T-0349 family 4,
  email-shape values). `_is_email_shaped` uses `email.utils.parseaddr` (an
  RFC 822 header parser, not a regex) plus a plain character-set validation
  of the parsed local/domain parts; `_line_marks_fake_email` mirrors
  `_secrets.py`'s `frob:secret-fake` marker convention (same literal marker
  string, textually shared so one comment discharges both gates);
  `_scan_python_email_values` walks every string-literal `ast.Constant` in
  a tracked `.py` file and fires PII011 on each unmarked email-shaped hit;
  wired into `pii_structural_gate`.
- tests/test_pii_structural_gate.py: new `TestEmailShapeValues` class (9
  cases): plain-address accept, display-name-wrapped reject (documented
  structural boundary), no-TLD-dot reject, obfuscated-`(at)` reject
  (evasion-shaped negative), plain-text reject, literal-fires,
  same-line/line-above fake-marker discharge, plain non-email literal
  does not fire. Fixtures deliberately build the email address via
  string concatenation (`"user" + "@" + "example.com"`), never an
  adjacent-literal-juxtaposition or bare top-level string constant in
  this test file's own source, so the fixtures cannot accidentally
  self-fire PII011 against tests/test_pii_structural_gate.py when the
  real gate scans its own tracked source.
- docs/modules/gates.md: documented PII011 in the rule table and the
  "Structural PII secrets detection T-0207" section.

Evidence:
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_accepts_plain_address
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_display_name_wrapped
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_no_tld_dot
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_obfuscated_at
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_plain_text
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_email_literal_fires
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_same_line_discharges
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_line_above_discharges
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_plain_string_literal_does_not_fire
- Full-file run: `uv run pytest tests/test_pii_structural_gate.py tests/test_secrets_gate.py -q` -> 84 passed
- `uv run frob test --base main` -> [PASS] python exit=0
- `uv run frob check --delta --ticket T-0349` -> gates 0 errors, 51 warnings
  (new PII011 WARN hits across the existing repo's own test fixtures --
  expected at default-on adoption severity, same posture as SEC110's
  initial rollout; none are ERROR-severity, so `frob check` stays green)

Filed: none this ticket (the T-0455 scope-narrowing bug affecting this
whole family was already corrected under T-0348's Done report and applies
identically here; not re-filed per ticket).

Gates: `uv run frob check --delta --ticket T-0349` clean (0 errors). ruff
check/format and ty both clean.

### Changed
```
 docs/modules/gates.md             |  22 +++--
 src/frob/gates/_pii_structural.py | 171 ++++++++++++++++++++++++++++++++++++--
 tests/test_pii_structural_gate.py |  70 ++++++++++++++++
 tickets.md                        |  70 +++++++++++++++-
 4 files changed, 317 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_accepts_plain_address` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_display_name_wrapped` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_no_tld_dot` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_obfuscated_at` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_is_email_shaped_rejects_plain_text` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_email_literal_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_same_line_discharges` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_line_above_discharges` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestEmailShapeValues::test_plain_string_literal_does_not_fire` (pytest node id, verified passing when recorded)
