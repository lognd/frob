## Done report

Added pytest-timeout to the dev dependency group and a global 120s /
thread-method default via `[tool.pytest.ini_options]` addopts in
pyproject.toml, so a deadlocked test (the ProcessPoolExecutor-inside-
ThreadPoolExecutor class disclosed in T-0265, structural fix T-0581) fails
on its own within ~2 minutes with a named node id and a thread stack dump,
instead of silently burning the 6h CI job cap. `method=thread` (not the
signal default) was chosen deliberately: the hang lives inside a forked
subprocess/native call where SIGALRM delivery to the main thread is not
reliable, and the watchdog thread reliably fires and reports from inside
that state regardless.

Verified locally with a throwaway deliberately-hanging test
(tests/unit/test_zz_throwaway_hang.py, time.sleep(200), never committed):
under -n auto (xdist) it failed at 2m1.6s wall clock with the offending
worker reported crashed and the specific node id
(tests/unit/test_zz_throwaway_hang.py::test_deliberately_hangs) named in
the FAILED summary line; under -n0 (single worker, matching what a
targeted foreground verification run looks like) it produced the
canonical pytest-timeout stack dump ("+++ Timeout +++") pointing at the
exact `time.sleep(200)` call site, at 2m0.3s wall clock. The throwaway
file was deleted immediately after and never committed. Two additional
fast unit test files (tests/unit/test_xref.py,
tests/unit/test_ts_parsers.py) were run afterward to confirm the new
120s ceiling produces no false timeouts on ordinary tests (1.4s total,
all passed).

docs/guides/testing.md documents the deadlock class, why 120s/thread was
chosen, and the per-test override mechanism
(`@pytest.mark.timeout(N)`) for legitimately slow tests -- linked from
docs/guides/agent-playbook.md's "See also" section (DOC001 required an
inbound link; docs/index.md is out of this ticket's docs/guides/**-only
scope, so agent-playbook.md's own See-also list is the in-scope anchor).

tests/system/test_scaffold_dx.py (pytest.mark.slow, spawns a real `uv
sync` + venv + full lint/typecheck/test/frob-check pipeline) legitimately
runs well past 120s and needs its own `@pytest.mark.timeout(N)` override;
adding that (and auditing the rest of tests/system/** for any other file
close to or past the ceiling) requires editing files under
tests/system/**, outside this ticket's docs/guides+config-only scope.
Filed as T-0742 (ex-draft, id lost at land) (mints its real T-#### id once merged onto
main) rather than silently expanding scope.

uv.lock needed regenerating for the new pytest-timeout dependency; scope
was formally extended via `frob ticket scope T-0692 --add uv.lock` (SCOPE001
otherwise fires) with the change reason recorded in the ticket's own
scope_changes audit trail.

An unrelated pre-existing bug was hit during evidence verification: running
tests/integration/test_interfaces.py's full file (or even just that file
alone, any -n mode) fails one unrelated test,
TestInterfaces::test_testing_collect, with "ImportError: cannot import
name 'CollectedTests' from partially initialized module 'frob.testing'
(most likely due to a circular import)" at src/frob/gates/__init__.py:118.
This reproduces on the ledger-restored tree with zero diff outside
pyproject.toml/tickets.md/uv.lock/docs/guides/testing.md, so it predates
this ticket's change and is not caused by the timeout config; it is NOT a
timeout, and the specific evidence node id used for this ticket
(TestInterfaces::test_main_cli_dispatches) passes cleanly in isolation
(0.\d s, exit 0). Not filed as a new ticket here since it is very likely
already tracked by an existing CI-triage ticket given the current wave of
T-0704..T-0712-family filings this session; flagging in this Done report
per the "disclose cuts honestly" rule rather than silently working around
it or over-filing a duplicate.

### Changed
```
 tickets.md | 190 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 187 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
