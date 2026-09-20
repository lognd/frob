## Done report

T-3887 F-012: FLAGCOV001 imported the target project's own parser/config
module from FROB'S OWN interpreter (`frob.gates._docblocks_shared.
resolve_dotted_symbol`, a plain `importlib.import_module`), so it could
never resolve for a project whose own dependency versions differ from
frob's -- reporting UNRESOLVED forever, never MEASURED, for exactly the
consumer FLAGCOV001 exists to check.

Mechanism chosen (per this ticket's own "decide the mechanism" framing):
an import cannot be routed through a `uv run --project <root> <tool>`
argv the way ty/ruff/pytest were (T-3887/T-4125) because there is no
existing tool CLI to spawn. Instead, `frob.gates._flag_coverage` now
spawns a small resolver script (`_RESOLVER_SCRIPT`) inside the checked
project's own `uv run --project <root> python -c ...` environment
(reusing `frob.process._project_tool.project_tool_argv`, per the
dispatch brief's explicit instruction not to build a second mechanism).
The script resolves `parser`/`config`/`forwarded`, builds the parser,
and prints back ONLY plain JSON (dest names, pydantic field names,
forwarded names) -- never a live object across the process boundary.
`find_dropped_cli_flags`'s own actual compare step (`_all_parser_dests(
parser) & frozenset(config_cls.model_fields) - forwarded`) is pure set
arithmetic over names, so `_check_source` now does that arithmetic
itself in frob's process once the three name sets come home, instead of
calling `find_dropped_cli_flags` on live objects.

Enumeration (this ticket's own instruction, "this is likely not the
only one"): `frob.gates._docblocks_shared.resolve_dotted_symbol` has
nine OTHER callers (_arch_schema.py, _docblocks_schema.py,
_dup_graph_schema.py, _gates_schema.py, _native_schema.py,
_profile_schema.py, _refs_schema.py, _test_runner_schema.py,
_testing_schema.py, _toplevel_scalar_schema.py) -- the same T-2390-family
schema-validator gates, same in-process-import defect shape. Filed as
T-4158 (a follow-up, generalizing this ticket's own resolver
into a shared helper those nine could reuse) rather than folded into
this ticket, which was scoped to FLAGCOV001's parser import specifically.

Off-repo fixture requirement (T-3887's own doctrine): a new test,
test_project_dependency_not_in_frobs_own_interpreter_still_resolves,
asserts directly (not merely claims) that `cattrs` is NOT importable
from frob's own interpreter, then proves a fixture project declaring
`cattrs` as its own dependency resolves cleanly through the fix -- the
exact "importable from the project, not from frob" case pre-fix code
could never pass. All 9 tests in
tests/unit/test_flag_coverage_gate.py pass for real, each one
genuinely spawning `uv run --project <fixture>` (no resolution-step
mocking); `flag_coverage_gate(Path.cwd())` (this repo's own real
frob.toml/AppConfig/_build_parser) is still clean.

Gates: `frob check --ticket T-4147` -- gate:OPAQUE clean (the
OPAQUE001 hit on `_RESOLVER_SCRIPT`'s embedded `importlib.import_module`
substring, a string literal never executed by frob's own interpreter,
is waived with a reason tying it to `resolve_dotted_symbol`'s own
existing, already-accepted OPAQUE001 waivers for the identical dotted-
path opacity). `ruff`/`ty` clean on the touched files. Two pre-existing
conditions left unaddressed as out-of-scope, same posture T-4146 (this
sprint's sibling ticket) already took on the identical file-fan-out
problem: AFFECT001 wants docs/modules/gates.md's FLAGCOV001 anchor
touched in this diff, and SCOPE002 flags that anchor (plus two
private-helper edges) as outside this ticket's declared scope --
docs/modules/gates.md is a shared god-doc carrying every gate's own
anchor (T-4146's own SCOPE002 fan-out measured 347 closure warnings on
adding it to scope), so widening this ticket's scope to it would be the
scope overreach the agent playbook warns against. gate:COV/gate:DOC/
gate:DRIFT/gate:ARCH103's remaining errors are all in files this ticket
never touched (src/frob/process/_project_tool.py, src/frob/vet/
_bare_toolchain.py, tickets/T-4144, tickets/T-4155, src/frob/check/
_python.py, src/frob/app/ticket_runner/_land_cmd.py) -- pre-existing,
unrelated to this diff. Filed: T-4158 (see above).

### Changed
```
 src/frob/gates/_flag_coverage.py      | 366 ++++++++++++++++++++++------------
 tests/unit/test_flag_coverage_gate.py |  94 ++++++++-
 tickets/T-4147/ticket.md              |  34 ++++
 tickets/T-4158/ticket.md    |  39 ++++
 4 files changed, 406 insertions(+), 127 deletions(-)
```

### Evidence
- `tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_project_dependency_not_in_frobs_own_interpreter_still_resolves` (pytest node id, verified passing when recorded)
- `tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_now_fire_reports_the_genuinely_dropped_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_this_repos_own_frob_toml_reports_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 4516 warning(s), 935 waived
- error-findings: AFFECT001@src/frob/gates/_flag_coverage.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, DOC006@tickets/T-4144/ticket.md, DOC006@tickets/T-4155/ticket.md, DRIFT002@src/frob/check/_python.py, SCOPE002@tickets.md
