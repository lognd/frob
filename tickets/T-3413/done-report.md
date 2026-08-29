## Done report

BEFORE (main post-T-3350-land, caches cleared via --no-cache, no REPLAY):
  SYS003 x3   src/frob/gates/__init__.py:284, src/frob/tickets/_scope_coverage.py:4,
              tests/unit/test_nodeid.py:11 -- undeclared cross-component import of
              the new frob.nodeid
  SELFAUDIT001/SYS102 x1  src/frob/nodeid.py has no node's code= glob binding it
  TEST001 x2  src/frob/lang/__init__.py:1090, src/frob/lang/_extract.py:538 --
              extract_import_edges has no unit test
  WIRE002 x1  src/frob/nodeid.py:25 -- the WIRE001 waiver on symref_to_nodeid is
              missing follow_up="T-####"
  = 7 findings, 4 distinct rules -- matches the coordinator's 6-item count if
  SYS003's 3 instances are read as one line item; matches T-3413's own filed
  count of 9 identities MINUS the 3 that are NOT T-3350-attributable (OPAQUE001
  on src/frob/_cli_parsers/_ticket/_metadata.py, already attributed to T-3404;
  2x DOC006 on tickets/T-3410 and T-3411's own docs, UNATTRIBUTED and unrelated
  to nodeid). Reconciled: T-3413's 9 = 6 T-3350-attributable (SYS003 x3,
  TEST001 x2, WIRE002 x1) + 3 unrelated. My own SELFAUDIT001/SYS102 finding
  was NOT in T-3413's filed list at all -- the post-land sweep's identity
  model apparently does not track SELFAUDIT001 the same way; it is real
  (reproduced directly against sys_gate) and is fixed here too.

ROOT CAUSE, per the brief: creating src/frob/nodeid.py added a module to the
tree without adding it to the DESIGN MODEL (design/frob.strata), so it was
__foreign__ to every component importing it.

(a)-vs-(b) DECISION, MADE EXPLICITLY: chose (b), NOT (a). frob.nodeid does
NOT get its own new `node` -- it joins the EXISTING `core` node's code= glob
instead. core already IS the "dependency-free leaf utility" bucket --
gitio.py/excludes.py/yamlio.py/tomlio.py/repo_meta.py/derived_state.py sit
there for the exact reason frob/__init__.py's own docstring gives for
re-exporting some of them ("used across nearly every sub-package"). The three
components that import frob.nodeid (gates, tickets_ledger, testsuite)
ALREADY have flows into core (f_gates_core, f_tickets_core, f_testsuite_core)
-- so (b) needs ZERO new Flow declarations, where (a) would need three new
flows for the identical effect. This does NOT undo T-3350's extraction: the
code still lives at src/frob/nodeid.py, is still not re-exported from
frob/__init__.py, every caller is unchanged -- only which node's code= glob
is considered to own the file changes. Reasoning recorded as a comment
directly above `node core` in design/frob.strata.

WIRE002: did not invent a follow-up id or point at a closed ticket. Fixed the
underlying gap instead -- gates/__init__.py and tickets/_scope_coverage.py
now import `symref_to_nodeid` under its real name (dropped the
`as _symref_to_nodeid` alias), so static call-graph analysis sees every real
call site directly. A WIRE001 waiver was the wrong mechanism for a permanent
alias choice; removing the alias removed the need for a waiver at all.

TEST001: added tests/unit/test_extract_import_edges.py, 8 tests covering all
six shapes plus two extras (dotted TYPE_CHECKING, same-name mixed
import_time=True/False) -- module-level (True), function-local (False),
class-body (False), if TYPE_CHECKING: (False), try/except ImportError (True),
if sys.version_info: (True).

AFTER (same measurement method, caches cleared, no REPLAY): SYS003 0/3,
SELFAUDIT001/SYS102 0/1, TEST001 0/2, WIRE002 0/1 -- all six (seven) findings
gone. Two follow-on findings my own fix introduced were also cleared in the
same pass: AFFECT001/COV002 on the renamed call sites (added frob:ticket
T-3413 + an AFFECT001 waiver where the change was a pure rename with no
behavior change), and a SELFAUDIT001/SYS100 fs.write gap on the new test file
itself (added it to testsuite's declared fs.write list).

test_sys_gate_zero_violations (tests/system/test_frob_self_model.py) still
FAILS after this fix -- but now ONLY for 6 unrelated, pre-existing findings
(SELFAUDIT001/SYS100 fs.read gaps on src/frob/process/_proc_scan.py x5 and
src/frob/stats/_agentic_shared.py x1, traced to T-3396 and T-3059
respectively, both already-closed tickets unrelated to T-3350). One of those
two (_agentic_shared.py) is already tracked at T-3409 (queued); filed the
other (_proc_scan.py) as T-3416 rather than leaving it untracked.
tickets/T-3388/ticket.md's frob:waive BUG002 follow_up="T-3413" is
INTENTIONALLY LEFT IN PLACE, not cleared: its premise (test confounded by
T-3350's regression) is now half-resolved by this fix, but the test still
fails for the other, unrelated half (T-3409 + T-3416) -- clearing
it now would be a false "fixed" claim. It should come out once T-3409 and
T-3416 both land.

### Changed
```
 tickets/T-3413/ticket.md | 9 +++++++++
 1 file changed, 9 insertions(+)
```

### Evidence
- `tests/unit/test_extract_import_edges.py::test_module_level_import_is_import_time` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_import_edges.py::test_function_local_import_is_deferred` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_import_edges.py::test_class_body_import_is_deferred` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_import_edges.py::test_type_checking_import_is_deferred` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_import_edges.py::test_dotted_type_checking_import_is_deferred` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_import_edges.py::test_try_except_import_error_is_import_time` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_import_edges.py::test_sys_version_info_guarded_import_is_import_time` (pytest node id, verified passing when recorded)
- `tests/unit/test_extract_import_edges.py::test_mixed_module_and_deferred_import_of_the_same_name` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 11 error(s), 4555 warning(s), 859 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-1382/ticket.md, DOC006@tickets/T-3410/ticket.md, DOC006@tickets/T-3411/ticket.md, DOC011@docs/modules/tickets.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3413, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
