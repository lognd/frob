## Done report

Redo (coordinator REJECT, round 2): round 1 hand-maintained a kotlin
needle table locally in `_capability.py` and carved a permanent
`UNREGISTERED_SCANNED_LANGUAGES` exception into the T-0169 drift lock to
avoid touching `_capability_registry.py` (out of round-1 scope). The
coordinator correctly rejected this: it leaves kotlin scanned-but-
unregistered, the exact state the drift lock exists to forbid. The
coordinator authorized expanding T-0170's scope to
`src/frob/vet/_capability_registry.py`; this round does kotlin the same
way every other language lives there, with no escape hatch.

Changed:
tickets.md::T-0170 scope (added `src/frob/vet/_capability_registry.py`, per
  coordinator authorization)
src/frob/vet/_capability_registry.py::LANGUAGES (added "kotlin")
src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS (6 new kotlin
  entries: net x2 -- OkHttp/Retrofit, HttpURLConnection; exec x2 --
  Runtime.getRuntime().exec, ProcessBuilder; client_storage x2 --
  SharedPreferences, Room)
src/frob/vet/_capability_registry.py::CAPABILITY_MATRIX_EXCUSES (11 new
  kotlin excuses: eval, fs-write, fs, fs-read, env, ffi, install-hook,
  html_render, sql, fetch_url, deserialize -- every kotlin cell is now
  either patterned or excused, `unexcused_empty_cells()` filtered to
  language=="kotlin" is empty)
src/frob/vet/_capability.py::_EXT_LANGUAGE (kept: .kt/.kts -> "kotlin")
src/frob/vet/_capability.py (deleted `_KOTLIN_PATTERNS` and
  `UNREGISTERED_SCANNED_LANGUAGES` -- kotlin needles now come from
  `_compile_patterns()` like every other language; module docstring
  updated to say so)
tests/test_vet.py::TestCapabilityScan (kotlin fixtures unchanged from
  round 1: fire tests for net/exec/client_storage, one no-fire benign
  test, .kt/.kts language_for assertions -- same tests now exercise the
  registry-compiled path instead of the hand-maintained one)
tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock
  (reverted to the strict `assert SCANNED_LANGUAGES == frozenset(LANGUAGES)`,
  no subtraction; `.kt`/`.kts` samples kept in the consistency test)
tests/test_capability_registry.py::_LANG_EXT and ::_BENIGN_SOURCE (added
  "kotlin" -> ".kt" / "val x: Int = 1\n" -- this file auto-parametrizes a
  fire/no-fire fixture test per `DANGEROUS_OPERATIONS` entry, so the new
  kotlin registry rows needed a language bucket here too; caught by a
  `make coverage` run that failed on KeyError before this fix)
docs/modules/vet.md ("Implementation notes (T-0008, capability-scan
  slice)" section rewritten to describe the registry-backed kotlin column
  and its `MatrixExcuse` cells instead of the round-1 hand-maintained
  table)

Dropped: the round-1 follow-up draft ticket (`T-draft-af6f91ba`,
"migrate kotlin capability needles into _capability_registry.py") is no
longer needed -- this round does that migration directly. Its block was
removed from tickets.md per the coordinator's instruction.

Still disclosed, not fixed (out of declared scope): `frob check --ticket
T-0170` reports one remaining ERROR, `REL001` (public API changed since
0.14.0; bump to >= 0.15.0, `frob release stamp`) against `pyproject.toml`,
which is not in this ticket's scope even after the registry expansion.
Left for the coordinator to bump at land time.

Evidence: same 7 pytest node ids as round 1 (still collected and green,
now exercising the registry-compiled path):
tests/test_vet.py::TestCapabilityScan::test_kotlin_net_okhttp_detected
tests/test_vet.py::TestCapabilityScan::test_kotlin_exec_runtime_exec_detected
tests/test_vet.py::TestCapabilityScan::test_kotlin_client_storage_shared_preferences_detected
tests/test_vet.py::TestCapabilityScan::test_kotlin_benign_file_has_no_capabilities
tests/test_vet.py::TestCapabilityScan::test_language_for_known_and_unknown_extensions
tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages
tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_language_for_is_consistent_with_scanned_languages
`uv run pytest -q tests/test_vet.py tests/unit/strata/test_selfconform.py`
ran green (no failures) after this round's change. `make coverage` (`uv
run pytest --cov=src/frob --cov-branch --cov-report=xml -q`, full suite)
was run TWICE in the foreground: the first run failed loudly
(`KeyError: 'kotlin'` in the new `tests/test_capability_registry.py`
auto-parametrized fixtures, 18 failing cases) because that file's
`_LANG_EXT`/`_BENIGN_SOURCE` tables did not yet know about the new
`kotlin` `DANGEROUS_OPERATIONS` rows; fixed per the Changed section above,
then the full suite re-ran and completed exit 0, and
`frob check --stamp-coverage` stamped file coverage. Re-recorded via
`frob ticket evidence T-0170 <ids>` after the redo (still 7 evidence ids
on the ticket). Additionally verified directly: `unexcused_empty_cells()`
filtered to `language == "kotlin"` is `[]` and `LANGUAGES` now includes
`"kotlin"`.

Gates: `uv run frob check --ticket T-0170` -- 1 error (`REL001`: public
API changed since 0.14.0 -- now reported as a "major" bump, up from
round 1's "minor", because this round adds real public registry surface
(`LANGUAGES` membership, new `DANGEROUS_OPERATIONS`/`CAPABILITY_MATRIX_EXCUSES`
entries) rather than round 1's `_capability.py`-local constant; still out
of this ticket's scope, disclosed for the coordinator to bump), 11
warnings, 203 waived (pre-existing repo-wide waivers, none newly added by
this change). `ruff check` and `ruff format --check` both clean on every
touched file. `frob ticket sweep T-0170` was re-run twice: once after the
scope expansion, once more after the `test_capability_registry.py` fix,
to keep PRE001 clean. No
frob:waive added by this ticket.
