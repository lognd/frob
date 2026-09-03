## Done report

Identified the exact call sites from the Windows CI log (run
33035660969, job 98397679871): tests/test_vet.py:5124 and :5134 in
TestObfuscationEnsemble.test_bidi_override_detected_in_c_file/kotlin_file
each plant a U+202E RIGHT-TO-LEFT OVERRIDE character via
Path.write_text() with no explicit encoding, so on Windows the platform
default (cp1252/charmap) codec raises UnicodeEncodeError before the
test can even set up its fixture -- the two windows-only charmap
failures T-3076 measured, verified byte-for-byte against the CI log.

Fixed at the source: both write_text() calls now pass encoding="utf-8"
explicitly. The read side (src/frob/vet/_obfuscation.py's
_scan_directory_obfuscation, via read_text) already pinned
encoding="utf-8" -- confirmed via git grep, no change needed there.
Surveyed the rest of tests/test_vet.py's ~250 other write_text() calls:
all write pure-ASCII fixture content, which round-trips fine through
any single-byte codec, so per the ticket's own instruction this stayed
a 2-line fix, not a repo-wide encoding audit.

Updated docs/design/windows-portability.md with a Primitive bucket
status table recording all five T-3076 buckets' current state,
including this ticket's charmap bucket now closed.

Evidence:
tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_c_file -- PASS
tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_kotlin_file -- PASS
Full tests/test_vet.py::TestObfuscationEnsemble: 12 passed
frob test --base main: the touched doc file (docs/design/windows-portability.md)
triggers select_tests' unknown-language suite-wide fallback across
python+rust, exceeding the 540s budget -- relied on the scoped pytest
run above per the series' own instructions instead.

Filed: none

Gates: frob check --ticket T-3510 --only coverage,drift,docstatus,tickets
reports no finding against tests/test_vet.py's touched tests or
docs/design/windows-portability.md; the repo-wide errors reported
(gate:COV 1, gate:DRIFT 47, gate:TICK 2, gate:WAIVE 3) are pre-existing,
same shape as measured on T-3508's check run in the same series.

### Changed
```
 tickets/T-3510/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_c_file` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_kotlin_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 18 error(s), 4133 warning(s), 874 waived
- error-findings: ARCH103@src/frob/tickets/_leases.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3510, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
