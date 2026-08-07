## Done report

Added `frob.arch._async_hazards` (T-0696, child 3 of T-0693): four
detectors over one parsed python file's functions -- `blocking-call-in-
async` (curated table: `time.sleep`, `requests.get/post/put/delete/patch/
head/request`, `urllib`'s `urlopen`, `subprocess.run/call/check_call/
check_output`, a future's `.result()`, the builtin `open()` -- reachable
inside an `async def` without a `run_in_executor`/`to_thread` dispatch
enclosing the call site), `nested-event-loop` (`asyncio.run`/`.run_until_
complete` reachable inside an `async def` body), `unawaited-coroutine` (a
call whose immediate parent is a `block` -- a bare top-level statement,
tree-sitter-python's own shape for an unwrapped statement call -- naming a
function this module itself declares `async def`), and `async-zero-
awaits` (an `async def` with no `await` anywhere in its own scope, not
crossing into a nested function's body; suggestion severity, feeds
T-0698's IO/CPU-bound advisory per that ticket's own text). Wired into
`frob.arch.__init__`'s python per-file pass alongside `_concurrency`'s
fork/pool family (skips test files, same as that family). Four new
`ArchCategory` values added to `_models.py` -- same unwaivable advisory
channel as every other `frob.arch` category, no `frob.gates` change
needed.

Changed:
- `src/frob/arch/_async_hazards.py` (new)
- `src/frob/arch/_models.py::ArchCategory` (4 new category values)
- `src/frob/arch/__init__.py::_run_python_checks` (wiring call + docstring
  note)
- `tests/unit/test_arch.py::TestAsyncEventLoopHazards` (new, 8 tests)

Evidence: `uv run pytest tests/unit/test_arch.py -k
TestAsyncEventLoopHazards -p no:cacheprovider -q` -> 8 passed. Confirmed
zero false positives: `analyze_project(Path("src/frob"))` against frob's
own tree returns 0 hits across all four new categories. `uv run frob check
--ticket T-0696 --only lint` / `--only gates-fast` / `--only gates-native`
all 0 errors. `uv run frob test --base main` -> `[PASS] python exit=0`,
10 test outcomes recorded.

Disclosed gap: `uv run frob check --ticket T-0696 --only gates-security`
shows 2 unwaived `SELFAUDIT001` findings on `src/frob/arch/
_async_hazards.py` (capability `net`/`exec` "observed" at the lines
holding `_BLOCKING_CALL_TABLE`'s `requests.*`/`subprocess.*` regex
strings) -- a false positive of the exact class already fixed for
`_srp.py` (T-0729) and `_logging_checks.py` (T-0910): the self-audit
scanner keys on string-literal CONTENT for evasion detection, so a
curated classifier table that merely *names* these substrings as data
reads as live capability usage even though this module does no such I/O
itself. The fix (`src/frob/vet/_capability.py`'s `_SELF_PATTERN_SUFFIXES`)
is outside T-0696's declared scope (`src/frob/arch/**`, `tests/unit/
test_arch.py`), so it is filed separately rather than fixed inline.

Filed:
- T-0914 (docs): add an "async event-loop hazards" section to
  `docs/modules/arch.md` (out of T-0696's scope, unlike sibling T-0695
  which had docs in scope) -- a `frob:waive COV001` placeholder is left on
  `_check_async_event_loop_hazards` until this lands.
- T-0915 (bug): add `("frob", "arch", "_async_hazards.py")` to
  `src/frob/vet/_capability.py`'s `_SELF_PATTERN_SUFFIXES` to clear the
  SELFAUDIT001 false positive disclosed above.

Gates: `frob check --ticket T-0696 --only lint/gates-fast/gates-native`
clean (0 errors each, re-verified after a `frob ticket sweep T-0696`
re-run following the last edit). `gates-security`'s 2 SELFAUDIT001
findings are a disclosed, out-of-scope gap tracked by T-0915
(not waived in-line since the fix lives in a file outside this ticket's
scope).
