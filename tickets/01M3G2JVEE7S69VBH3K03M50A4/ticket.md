+++
id = "01M3G2JVEE7S69VBH3K03M50A4"
title = "frob test --base selects module-level names (tests/...::_TOML) as test ids from the touched symbol set and exits 4 while plain pytest passes; selection must come only from collected pytest items"
type = "bug"
category = "triage"
priority = "high"
points = 2
reporter = "agent"
created = "2026-09-27T00:00:00Z"
updated = "2026-10-04T21:07:19Z"
aliases = ["T-6606"]
labels = ["milestone:0.535.0", "v1-cluster:C4a"]
scope = ["src/frob/testing/_collect.py", "src/frob/testing/_select.py", "docs/modules/testing.md"]

[[links]]
kind = "duplicates"
target = "01M1T07NZ6Z8S8P3AQVVZBDJTE"
+++

Reported by the crunk session (2026-09-26, crunk T-0211): `frob test
--base main` selected module-level constants as test ids
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->(tests/integration/test_int_02_ingest_fs.py::_TOML and
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->tests/integration/test_int_11_jsx.py::_TOML) and exited 4, while plain
pytest on both files passes. The touched-symbol walk hands every changed
symbol in a test file to the runner as `file::name`, so a module-level
constant that changed (or that carries a frob:tests binding) becomes a
node id pytest cannot collect, and the run fails on selection rather
than on a test.

Deliver: test-id selection intersects the touched symbol set with the
items the language collector actually reports (pytest functions,
methods and parametrized ids; NUnit [Test] methods for C#), never bare
module names; a touched non-test symbol inside a test file selects the
tests of that file (a changed fixture or constant means its consumers
must run), and the run log lists the symbols it widened this way. This
is the token/grammar rule (decide from parsed symbols and collected
items, never from names). Positive control: a fixture test module with a
changed module-level constant and two tests; `frob test --base` runs
both tests and exits 0, and the selection log names the constant as
"widened to file".
