## Done report

Changed:
tests/unit/test_wire001_multiprocessing_target.py (new)
tests/unit/test_fix_engine_journal.py::_write_journal_and_block (frob:waive WIRE001 removed, dead)

Evidence:
tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget::test_function_passed_as_process_target_kwarg_is_not_flagged
tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget::test_function_passed_as_context_process_target_kwarg_is_not_flagged
tests/unit/test_wire001_multiprocessing_target.py::TestWire001MultiprocessingProcessTarget::test_function_with_no_process_target_caller_anywhere_still_flagged

Investigation finding: src/frob/gates/_wire.py's WIRE001 analyzer already
resolves multiprocessing.Process(target=X)/ctx.Process(target=X) correctly
-- this is the generic keyword-argument-value shape T-2778 already landed
(_wire_reach_patterns's keyword_arg_pattern, gated to kind==FUNCTION):
target=X is textually indistinguishable from any other name=X keyword
argument. Verified empirically: forced _write_journal_and_block to appear
"new in this diff" (git-diff-visible def line change) with the waiver
removed and multiprocessing.get_context(...).Process(target=..., args=(...))
still present on its own real caller -- WIRE001 did NOT fire. No detector
code change was needed or made.

Fix: added tests/unit/test_wire001_multiprocessing_target.py (must-fire/
must-stay-quiet fixtures naming multiprocessing.Process(target=...) and
ctx.Process(target=...) by name, following T-2778's own
test_wire001_callback_keyword_argument.py pattern via wire_gate directly)
to lock this in explicitly, since no prior test named the shape by name.
Removed _write_journal_and_block's now-obsolete frob:waive WIRE001.

Filed: none

Gates: frob check --ticket T-3576 clean on gate:SCOPE/gate:PRE (sweep
refreshed). Repo-wide failures from an unscoped run are pre-existing
(T-3590). BUG002/designate-repro not applicable (kind=feature).
