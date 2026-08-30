## Done report

Root cause (bucket E, T-3488): _first_invalid_scope_glob's ONLY validity
check was probing each scope entry through pathlib.Path.glob and
catching ValueError/NotImplementedError -- relying entirely on CPython's
stdlib glob-pattern compiler to reject a ";"-joined entry (e.g.
'src/frob/verify/**;src/frob/app/ticket_runner/**') via its "'**' can
only be an entire path component" rule. Measured locally (Python
3.10.12): this DOES raise. The macOS CI run (33311990183) measured the
identical entry ACCEPTED (no raise) -- CPython-version/build-dependent
stdlib glob behavior, not something this function should have been
betting the whole check on.

Fix: added an explicit, portable pre-check -- any scope entry containing
a literal ";" is refused directly (return glob) before ever reaching
the Path.glob probe. A ";" is never a legitimate character in any glob
this module's own positive-control list (test_every_existing_valid_
form_still_passes) accepts, and is exactly the delimiter-confusion
shape T-2450's real incident was about, so this closes the gap
regardless of which Python build/version a given platform resolves.

Evidence: tests/test_tickets.py::TestScopeGlobValidation (all 7) run 3x
with -p no:xdist -- pass all 3 runs.

### Changed
```
 tickets/T-3498/ticket.md | 14 +++++++++++++-
 1 file changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestScopeGlobValidation::test_semicolon_joined_entry_is_invalid` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_new_ticket_refuses_a_semicolon_joined_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_every_existing_valid_form_still_passes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 22 error(s), 4128 warning(s), 868 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3498, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py
