---
id: T-4070
title: frob test's touched-set selector calls any symbol in a test file a test, so
  a module-level constant is emitted as a pytest node id
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_select.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer apollo, 2026-09-06:

  "`frob test --base main` SELECTION BUG: it collected a shared MODULE-LEVEL
   CONSTANT (`_TOML` in tests/integration/test_int_02_ingest_fs.py /
   test_int_11_jsx.py) AS A PYTEST NODE ID and failed on files UNTOUCHED BY THE
   DIFF (T-0132 implementer, REPRODUCIBLE after re-run and sweep). The touched-set
   selector appears to treat cross-module constant imports as test nodes.
   Workaround: bare full-suite pytest."

VERIFIED IN OUR SOURCE. src/frob/testing/_select.py:115:

    def _looks_like_test_symbol(symref: str) -> bool:
        path, sep, qualname = symref.partition("::")
        if is_test_file(path):
            return True
        return sep == "::" and qualname.split(".", 1)[0] == "tests"

THE HEURISTIC IS FILE-BASED, NOT SYMBOL-KIND-BASED. Any symbol whose PATH is a
test file is declared a test -- so a module-level constant, a helper function, a
fixture, a dataclass, or an imported name defined in a test file all qualify.
`_TOML` is a constant; the selector calls it a test, hands it to pytest as a node
id, and pytest fails because there is no such test.

THAT ALSO EXPLAINS THE SECOND HALF OF THEIR SYMPTOM -- failures on files the diff
never touched. `_TOML` is shared ACROSS modules, so once the selector treats it as
a test symbol, the ripple pulls in every module importing it. A constant
misclassified as a test does not just add one bad node id; it drags unrelated
files into the touched set.

WHY THE FILE-PATH SHORTCUT EXISTS, and why the fix must not simply delete it: the
docstring explains the second branch handles Rust inline `mod tests { ... }`
symbols that live in the same source file as the code they cover, "so the file-
path check alone would call neither endpoint a test". So the author was thinking
about the case where path is INSUFFICIENT, and did not consider the case where
path is INSUFFICIENTLY SPECIFIC. Both branches are about locating tests; neither
asks what KIND of symbol it is.

THE FIX: consult the symbol's KIND, which the graph already carries
(SymbolRecord), rather than inferring test-ness from its file. A test is a
function/method whose name matches the runner's convention -- not "anything
declared in a test file". Verify what kind information is available at this call
site before designing; if the selector only has a symref string here, the fix may
be to pass the record rather than to improve the string heuristic.

THIS IS THE THIRD FILE-PATH-AS-PROXY-FOR-KIND DEFECT THIS DRIVE, and they are
worth reading together because the shape recurs:
  T-4042  a pytest-shaped id validator rejected legitimate deep cargo ids,
          justified by "a shape no real pytest node id ever takes"
  T-4064  REF002 resolved alias TS imports but not relative ones
  this    a symbol is a test because of the directory it lives in
Each substitutes an easily-computed property for the one actually meant.

NOTE THE COST SHAPE: the workaround is "bare full-suite pytest", i.e. the consumer
abandoned touched-set selection entirely. A selector that can produce invalid node
ids is worse than no selector, because its failure looks like a test failure
rather than a selection failure -- the user chases a red test that does not exist.

MUST-FIRE FIXTURE: a genuine test function in a touched test file is still
selected.
MUST-STAY-QUIET: a module-level constant (and a helper, and a fixture) in a
touched test file is NOT emitted as a pytest node id.
THIRD FIXTURE: a constant shared across test modules does not pull untouched
modules into the selection.

ACCEPTANCE
- Test-ness determined from symbol kind, not file path; the Rust inline
  `mod tests` case still handled.
- What kind information is available at the call site, established first.
- All three fixtures committed.