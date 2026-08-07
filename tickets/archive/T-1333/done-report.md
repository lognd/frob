## Done report

Implemented the fallback the ticket's own investigation direction suggested:
_yaml_loader() now detects an active coverage.py trace function via a new
_coverage_tracer_active() helper (keyed on sys.gettrace()'s callable
__module__ starting with "coverage") and falls back to the pure-Python
SafeLoader in that case, even when libyaml/CSafeLoader is available.
SafeLoader accepts the same YAML subset as CSafeLoader (documented already
in T-1206's docstring), so this cannot change what parses, only which
loader runs under a coverage trace.

Scope was extended (frob ticket scope T-1333 --add) to
tests/unit/test_ticket_store.py (already hosts TestYamlLoader, the
natural home for a real behavioral test of the new fallback) and
docs/modules/tickets.md (AFFECT001 required the Storage internals section
to record the new _coverage_tracer_active symbol and the updated
_yaml_loader contract).

Honest disclosure: despite many attempts (bare coverage.py, pytest-cov,
the exact repo Makefile coverage.py subprocess rc with
concurrency=multiprocessing,thread, -n0 and -n4 xdist, 5x repeat loops,
running test_tickets_brief.py alone and together with
tests/unit/test_ticket_store.py) I could not reproduce the reported
"could not determine a constructor for the tag None" corruption directly
in this environment/pyyaml/coverage version combination. The fix is
implemented defensively per the ticket's own suggested mechanism and is
unit-tested directly (tracer detection, and the loader's fallback
decision), but I never observed the original corruption occur here to
confirm the fix actually eliminates it. If it does not reproduce under
the coordinator's coverage run either, this ticket's premise may need
re-investigation with the coordinator's exact environment.

### Changed
```
 tickets.md | 46 +++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 45 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_detects_coverage_tracer_by_module_name` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_no_active_tracer_is_not_coverage` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_under_active_coverage_tracer` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 601 warning(s), 693 waived
- error-findings: PRE001@tickets/T-1333
