## Done report

COORDINATOR CORRECTION (post-initial-report): the 136/142 tests/** findings
were misclassified in the first pass as "a real rule-level pattern needing
136 individual waivers." That was wrong -- per the standing "decide from
semantics, never a lexical match" directive, the right question was WHY
OPAQUE001 was firing on them at all.

How OPAQUE001 detected indirection (before this fix): a raw byte-level
substring scan (frob.vet._capability_scan._needle_construct_findings)
matching fixed needles ("setattr(", "eval(", "sys.modules[", ...) anywhere
in the file's text outside comments/string literals, with no check that
the match was a real call to the NAMED python builtin (or, for sys.modules,
a real WRITE). Investigating the actual 142 findings found this was the
dominant cause, not test-fixture string content as first assumed:

- pytest's monkeypatch.setattr(target, value) and z3's Model.eval(x) are
  dotted attribute/method calls -- "setattr("/"eval(" match as a trailing
  substring of "monkeypatch.setattr("/"model.eval(", but neither is
  python's builtin setattr/eval.
- A test function literally named test_..._exec / a helper named
  _mutation_for_eval -- the needle matches mid-token inside a longer
  identifier's own name (the identifier's def, not a call at all).
- sys.modules["frob.strata._facts"] used as a plain READ (an ordinary
  already-imported-module lookup for monkeypatch.setattr's own target) --
  the "sys.modules replacement" taxonomy row's own rationale is
  specifically about a WRITE (sys.modules[name] = fake_module replacing
  what subsequent imports resolve to), which the needle match cannot tell
  apart from a read.

What I changed (src/frob/vet/_capability_scan.py): two AST-based semantic
checks, using frob.lang.raw_tree's tree-sitter node info (the same parse
this ticket's own _enclosing_qualname already introduced for OPAQUE001's
symref), both fail-open (narrow the existing scan, never widen it):

- _python_bare_call_ok: for the bare-python-builtin needles (eval/exec/
  getattr/setattr/__import__), confirms the matched identifier is the
  UNQUALIFIED callee of a real call node -- False (suppressed) when its
  parent is an `attribute` node (dotted access) or when the match's start
  byte does not equal the enclosing identifier node's own start byte
  (mid-token substring).
- _python_sys_modules_write_ok: for "sys.modules[", confirms the matched
  subscript is the LEFT (assignment-target) side of an `assignment` node
  -- False (suppressed) for a bare read.

Both wired into _needle_construct_findings (extracted into a small
_semantic_check_suppresses helper to stay under ARCH001's line threshold)
BEFORE the existing literal-arg check runs, so a confirmed-false-positive
match is dropped before any "is the argument a literal" question is even
asked about it.

Re-measured (frob check --only opaque --json, gate:OPAQUE, repo-wide,
FROB_NO_GATE_CACHE=1 confirmed): 142 -> 1 unwaived error after the
semantic fix alone. The 136 tests/** false positives evaporated exactly
as predicted -- verified directly (not assumed): every one of the
dotted-call/mid-token-substring/sys-modules-read shapes above stopped
firing, confirmed by 6 new regression tests
(tests/test_vet.py::TestOpaqueIndirectionGate, T-1659-suffixed) locking
each false-positive shape suppressed AND the corresponding genuine bare
call/write still firing.

What genuinely remained after the semantic fix (10 findings before
handling, matching the earlier report's own classification):

- 3 "sys.modules replacement" (tests/unit/strata/test_facts.py:309,
  tests/unit/strata/test_parse.py:254, tests/unit/test_lang_strata.py:176)
  turned out to ALSO be semantic-check false positives (plain reads, not
  writes) -- caught and suppressed by the same
  _python_sys_modules_write_ok fix, not left as manual waivers.
- 1 genuine finding (tests/unit/test_dup_core.py:52, getattr(frob_core,
  name) over a closed literal tuple of kernel names) -- given its own
  narrow waiver, same closed-set rationale as the _config_external.py
  waivers below.
- 5 in src/frob/app/_config_external.py (_apply_path_fields/_apply_int_
  fields/_apply_float_fields/_apply_list_fields/_apply_bool_flags) -- the
  legitimate multi-function waiver identified in the first pass
  (_apply_string_fields's own T-1424 note: "this waiver now covers every
  _apply_*_fields helper below") that relied on the file-scope fallback
  T-1659's symref fix closes. Each sibling now carries its own copy of the
  identical closed-tuple rationale.
- 1 in src/frob/logging/filter.py:26 -- the _enclosing_src mis-binding bug
  identified in the first pass (filed separately as T-1667).
  Handled here (not deferred) so main can land at 0 errors: moved the
  existing waiver comment from inside __init__'s body to directly above
  `def __init__`, which binds correctly via the ordinary following-symbol
  rule without depending on the buggy trailing-comment path. Verified via
  frob check --only opaque: the finding now shows [waived: ...] instead of
  unwaived. The dsl.py root-cause bug itself stays tracked in
  T-1667 for whoever generalizes the real fix beyond this one
  site.

Final repo-wide measurement (frob check --only opaque --only cache, cache
BYPASSED via FROB_NO_GATE_CACHE=1): 0 errors, 25 waived. frob check
--land-parity: clean -- 0 unscoped error(s), matches what the land sweep
would see. All 445 tests/test_vet.py + tests/test_cache_gate.py +
tests/unit/test_dup_core.py tests pass (SUITE-RESULT: exitstatus=0).
gate:SCOPE/gate:PRE/gate:TEST/gate:ARCH/gate:FMT/gate:AFFECT --ticket
T-1659 all clean (0 errors).

Both successor tickets from the first pass stay open and unchanged:
T-1666 (PERF/PII/SEC005 symref sweep -- separately, not
affected by this semantic fix, which is OPAQUE001-specific) and
T-1667 (the _enclosing_src mis-binding bug, now with a
DIFFERENT confirmed reproduction site fixed around rather than at the
root: filter.py's own finding is now correctly waived, but the general
dsl.py defect remains open for other, not-yet-hit sites).

### Changed
```
 frob.lock                        |   2 +-
 src/frob/app/_config_external.py |  46 ++++-
 src/frob/gates/_cache_gate.py    |   2 +
 src/frob/gates/_opaque.py        |  38 +++-
 src/frob/logging/filter.py       |  16 +-
 src/frob/vet/_capability_scan.py | 149 ++++++++++++++-
 tests/test_cache_gate.py         |  27 +++
 tests/test_vet.py                | 124 +++++++++++++
 tests/unit/test_dup_core.py      |   5 +
 tickets.md                       | 379 ++++++++++++++++++++++++++++++++++++++-
 10 files changed, 770 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_violation_carries_symref` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_waiver_scoped_to_symbol_not_whole_file` (pytest node id, verified passing when recorded)
- `tests/test_cache_gate.py::TestCache001Symref::test_violation_carries_symref` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_dotted_setattr_call_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_dotted_eval_method_call_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_identifier_ending_in_builtin_name_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_bare_setattr_call_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_sys_modules_read_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_sys_modules_write_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 638 warning(s), 710 waived
- error-findings: none (measured, zero errors)
