## Done report

PORT001 meta-gate built, mirroring LEXCHECK001 (AST-scanning, allowlisted,
WARN tier, PARSE001/UNRESOLVED fail-loudly convention) per the ticket's own
directive not to invent a second detector architecture for this job class.

Two AST shapes flagged, both resolved against the SCANNED repo's own
pyproject.toml [project].name (never a hardcoded "frob" literal in the
detector itself, which would be exactly the bug class one layer up):
  PORT001-PATH: a "src/<pkg>/"-shaped literal passed to .startswith(...)
    -- the exact _env_var_docs.py/_root_asset_dirs.py shape.
  PORT001-IDENT: <pkg> as a whole /-delimited path segment inside a
    Tuple/List literal or a JoinedStr constant chunk -- generalizes past
    the self_match.py-style tuple-of-path-segments shape.

IMPORTANT CALIBRATION FINDING (coordinator's resequencing was correct):
a first cut of PORT001-IDENT matched pkg as a bare SUBSTRING anywhere in
an f-string constant chunk. Run unscoped against src/frob/gates/ (43
files), that produced 43 raw hits -- nearly all false positives: ordinary
prose mentioning this project's own CLI by name (f"frob ticket scope
{id} --add ...", f"frob:used-by <consumer>", f"frob:decision {target}
has no ..."), not path-building logic at all. Narrowed IDENT to require
pkg as a whole /-split segment of the constant chunk (so "src/frob/gates/"
matches, "frob ticket scope ..." does not). Re-run: 5 hits within
src/frob/gates/ (the only package this gate scans -- see below).

HONEST COUNT AND DELTA (coordinator's own request, not reconciled to
their number):
  PORT001 (AST, narrowed, src/frob/gates/ only): 5 files
    - _env_var_docs.py, _root_asset_dirs.py (PORT001-PATH, the two real
      .startswith bugs T-2389 already covers)
    - __init__.py, _lang_conformance.py, _wire.py (PORT001-IDENT --
      maintainer-facing message text pointing at this repo's own file,
      e.g. "add them to the order tuple (src/frob/gates/__init__.py)";
      arguably a lower-severity, different class than the silent-pass/
      false-positive behavioral bugs the epic body describes -- flagged
      as WARN for triage, disposition (fix vs waive) left to whoever
      picks up the follow-up)
  git grep -l '"src/frob/"' (exact quoted literal): 3 repo-wide, 2 in
    gates/ -- SMALLER than the epic's stated 22/14.
  git grep -l "src/frob/" (bare substring, no quoting): 153 repo-wide,
    37 in gates/ -- LARGER than 22/14.
  Neither grep variant reproduces the epic's own 22/14 count; PORT001's
  5-in-gates AST count sits between the two extremes and is offered as
  the trustworthy denominator going forward, not a reconciliation to any
  of the three.

SCOPE LIMITATION, disclosed not hidden: gates/__init__.py and
docs/modules/gates.md were both under T-2397's live lease for the
duration of this ticket (unrelated wiring work in the same registry
file) -- narrowed scope to _port_selfcheck.py + its own test file only.
PORT001 exists, is tested, and is importable, but is NOT yet wired into
frob check's own gate dispatch or documented in docs/modules/gates.md.
Filed as an immediate follow-up (cited below) to land once T-2397's
lease clears, rather than waiting idle on this ticket.

Also disclosed: _tracked_gate_files reuses the shared
tracked_python_files_for_gate helper (_walk_lint.py), which itself
hardcodes `git ls-files -- src/frob` -- the SAME literal-package-path
class T-2384 targets, one layer below PORT001/WALK001/RENDER001 alike.
Not fixed here (out of this ticket's scope); a natural T-2389 sibling.

### Changed
```
 tickets/T-2388/ticket.md | 27 ++++++++++++++++++++++++---
 1 file changed, 24 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_path_prefix_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_identity_literal_in_tuple_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_allowlisted_self_match_file_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_gate_code_never_scanned` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_clean_gate_module_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_search_literal_is_resolved_not_hardcoded` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_unresolved_project_name_is_not_a_clean_pass` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_port_selfcheck.py::TestPort001::test_unparseable_file_is_parse001_not_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_port_selfcheck.py, ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, DUP001@tests/unit/gates/test_port_selfcheck.py, E501@/home/logan/projects/frob/.claude/worktrees/port-selfcheck/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/port-selfcheck/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2388, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/gates/_port_selfcheck.py, WIRE003@docs/modules/cli.md
