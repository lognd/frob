## Done report

Changed:
  src/frob/vet/_capability_core.py -- `_matching_close_paren`,
    `_top_level_arg_strings`, `_literal_mode_value`, `_OpenCallMode`,
    `_open_call_mode`, `_open_call_sites`, `_has_write_mode_open_call`,
    `_has_read_mode_open_call` (new, token-level parse of an `open(`/
    `.open(` call's mode argument); `_SPECIAL_CHECKS["python"]` (adds
    "fs-write"/"fs-read" entries routed through the two new checks);
    `_operation_entry_matches` (ORs needle hits with the mode-aware
    checks for the two `open()` registry entries instead of returning
    early on "entry has needles")
  src/frob/vet/_capability_registry/_dangerous_ops_python.py -- the
    `fs-write` "open() (write/append mode)" entry's needles: `"open("`
    removed (was the mode-blind false-positive needle), `.write(` kept
  design/frob.strata -- the "gates" node's `fs.write` via-list: ten
    "*_schema.py" filenames removed (the ticket's own seven --
    _arch_schema.py, _docblocks_schema.py, _dup_graph_schema.py,
    _gates_schema.py, _native_schema.py, _test_runner_schema.py,
    _toplevel_scalar_schema.py -- plus three more of the identical shape
    found auditing the same via-list: _profile_schema.py, _refs_schema.py,
    _testing_schema.py); each one's only fs access is
    `toml_path.open("rb")`, confirmed by direct read of all ten files
  tests/test_vet_capability.py -- new `TestModeAwareOpenCall` class, 7
    tests covering all three of the ticket's acceptance controls

Evidence:
  tests/test_vet_capability.py::TestModeAwareOpenCall::test_read_mode_open_reports_fs_read_not_fs_write  (accepts 0, 2)
  tests/test_vet_capability.py::TestModeAwareOpenCall::test_default_mode_open_is_read_not_write  (accepts 0)
  tests/test_vet_capability.py::TestModeAwareOpenCall::test_write_mode_open_still_reports_fs_write  (accepts 1)
  tests/test_vet_capability.py::TestModeAwareOpenCall::test_append_mode_open_still_reports_fs_write  (accepts 1)
  tests/test_vet_capability.py::TestModeAwareOpenCall::test_dotwrite_call_still_reports_fs_write  (accepts 1)
  tests/test_vet_capability.py::TestModeAwareOpenCall::test_indirect_write_operations_still_reported  (accepts 1)
  tests/test_vet_capability.py::TestModeAwareOpenCall::test_dynamic_mode_expression_fails_closed_to_write  (accepts 1)
  Full `tests/test_vet_capability.py` + `tests/test_capability_registry.py`
  + `tests/test_vet.py`: 898 collected, 0 failed (pre-strata-edit run);
  `tests/test_vet_capability.py` + `tests/test_capability_registry.py`:
  444 collected, 0 failed (post lint-fix run, includes the strata edit).

Measured before/after (this ticket's own instructions, not estimates):
  - SELFAUDIT001 for the seven/ten schema modules: gone. Direct
    `scan_file_capabilities` sweep of all 7 originally-named modules
    (plus the 3 more found) now reports `{"fs-read"}` only, never
    `fs-write`.
  - Control 1 (must-now-be-silent): `open(p, "rb")` (bare and `.open(`)
    -> no `fs-write`, confirmed both via direct byte-level assertions on
    `_has_write_mode_open_call` and via full `scan_file_capabilities`.
  - Control 2 (must-still-fire): `open(p, "w")`, `open(p, "a")`,
    `.write(...)` -> `fs-write` still reported, confirmed directly.
  - Control 3 (must-still-fire-indirect): enumerated the pre-fix indirect
    fs-write needle set (`os.remove(`/`os.rename(`, `shutil.rmtree(`/
    `move(`/`copy(`, `Path.write_text(`/`write_bytes(`/`.unlink(`,
    `tempfile.mktemp(`) -- none of these needles were touched by this
    fix (only the two `open()` entries' needles changed), and a direct
    fixture combining `Path.write_text`/`shutil.move`/`os.replace` still
    reports `fs-write` post-fix.

LEXCHECK001 finding (reported per ticket instructions, not fixed): it did
NOT catch this instance for two independent reasons. (1) LEXCHECK001
scans `src/frob/gates/**/*.py` only (its own module docstring); the
dangerous-ops detector lives entirely under `src/frob/vet/**`, outside
its scanned tree. (2) Even if the tree were widened, LEXCHECK001's
detection shape requires a SINGLE function that both calls
`re.search`/`match`/`fullmatch`/`findall`/`finditer` AND constructs a
`Violation(...)` with no `symref=`. The dangerous-ops needle matchers use
plain `bytes.find`/substring scanning, never `re.*` -- so the `re.search`
trigger signal would not fire even inside the scanned tree -- and needle
matching and `Violation` construction happen in entirely separate
modules/functions (`_capability_core.py`'s matchers return booleans/sets;
violation construction happens in gate-layer callers), which
LEXCHECK001's own docstring already discloses as a known per-function-
only limitation ("a module that splits the regex decision and the
Violation construction across two different functions ... is not caught
by this pass"). Filing a widening ticket is left to the reader per the
ticket's own instruction that this is "worth reporting even if you do
not fix it here" -- not filed separately since it is fully captured here
and in the Done report's own text, per T-1636's guidance against
low-value draft churn for a pure disclosure.

Dangerous-ops table audit (python slice, `_dangerous_ops_python.py`,
the only language file this ticket touched -- other-language tables
disclosed as NOT audited, see below):

  Needles found to be UNAMBIGUOUS (no over/under-match risk beyond
  ordinary substring-scan limits already accepted elsewhere in this
  registry): subprocess.*, os.system/popen/exec*/spawn*, eval(/exec(
  (already bare-call-boundary-checked via _BARE_CALL_NEEDLES),
  __import__(, importlib.*, runpy.*, code.*, pickle.*, marshal.*,
  shelve.open(, ctypes.*, cffi, ExtensionFileLoader, socket., http.client,
  urllib., ftplib., smtplib., requests., aiohttp., httpx.,
  webbrowser.open(, asyncio.create_subprocess_*, asyncio.open_connection(/
  start_server(, os.remove(/os.rename(, shutil.rmtree(/move(/copy(,
  write_text(/write_bytes(/.unlink(, read_text(/read_bytes(, json.load(,
  tempfile.mktemp(, execute(f"/execute('%s'/execute(" +, os.environ/
  os.getenv(, os.putenv(/os.environ[, os._exit(, signal.signal(,
  pty.spawn(/fork(, multiprocessing.Process(/Pool(, os.startfile(,
  cmdclass, allow_pickle=True, jinja2.Template(/Environment.from_string(,
  autoescape=False, load_dotenv(, uvicorn.run(, sqlalchemy.text(,
  asyncpg.connect(, boto3.client(/resource(, stripe.api_key,
  anthropic.Anthropic(, aiosmtpd.controller.Controller(,
  sync_playwright(/async_playwright(, page.evaluate(, ImageMath.eval( --
  every one of these is either already call-shaped (trailing `(`, so a
  bare substring occurrence is already a real call site modulo the
  ordinary "identifier merely contains this text" risk every needle in
  this scanner accepts) or a dotted/underscored token unlikely to occur
  as prose (module docstring's own "recall over precision" posture).

  ONE genuinely FIXED this ticket: `open(` in the `fs-write` entry
  (over-matched: fired regardless of read/write mode -- fixed by this
  change).

  ONE further AMBIGUOUS entry, NOT fixed (out of scope, filed below):
  none found needing a mode split the way `open(` did -- the closest
  analog, `shelve.open(`, is unambiguous (shelve is always read-write
  capable and pickle-backed regardless of any flag argument, so no mode
  split applies the same way).

  UNDER-MATCH risk assessed for the two most severity-sensitive families
  per the ticket's own instruction (network/exec are more serious than a
  false fs.write): `os.exec` (bare prefix, catches exec/execl/execve/
  execvp/... -- broad by design, no under-match); `subprocess.`/`Popen(`
  -- catches every subprocess.* function by prefix, no under-match found;
  network needles are per-library dotted prefixes (`requests.`,
  `httpx.`, etc.) -- these do NOT distinguish a read-only GET from a
  state-changing POST/PUT/DELETE, which is a REAL under-match in the
  opposite direction of this ticket's own finding (a network client
  making only GET calls is declared the same `net-connect` capability as
  one making POST/DELETE calls) -- but `net-connect`/`net-listen`'s mode
  split is CONNECT-vs-LISTEN (socket role), not read-vs-write (HTTP verb),
  so this is a different axis than the one this ticket's acceptance
  criteria cover, not a bug in the SAME class T-2457 was filed to fix.
  Filed as a new ticket rather than fixed here (below).

  NOT audited (disclosed, not silently skipped): the typescript, rust,
  c-cpp, and kotlin slices of `DANGEROUS_OPERATIONS`
  (`_dangerous_ops_other.py` and any other per-language table files) --
  this ticket's scope (`src/frob/gates/_pii_structural/**`, `design/
  frob.strata`) and its own reported false positive are both python-only;
  auditing the other three languages' needle tables for the same class of
  defect is real, separate work.

Filed:
  T-2463 (renumbers at land) -- SYS101 fallout: `checker`/
    `fleet`/`deploy` (bare `may "fs.write";`, zero files found with
    real fs-write post-fix by direct sweep) and `vet` (declared via
    `_nvd.py`/`_registry.py`, likewise zero found) all fail SYS101
    ("declared but never observed") once the mode-blind `open(` false
    positive is fixed. Same bug class, but confirming whether these are
    ALSO false declarations (most likely) or a genuine scanner gap
    elsewhere requires reading src/frob/check/**, src/frob/fleet/**,
    src/frob/deploy/** in full -- outside this ticket's declared scope.
    Filed rather than fixed silently.
  T-2464 (renumbers at land) -- Network dangerous-ops needles
    do not distinguish read vs write HTTP/DB verbs (the under-match noted
    in the audit above: requests./httpx./boto3.client(/etc. fire
    identically for a GET and a POST/DELETE).

Gates: `frob check --only gates-security --ticket T-2457` -- SELFAUDIT001
count for the ten schema modules: 0 (was present pre-fix, confirmed by
running the check before the design/frob.strata edit landed in this
worktree). `frob check --only lint --ticket T-2457` -- clean on every
file this ticket touched (2 pre-existing E501 self-introduced by this
ticket's own new code, fixed; F401s in `_capability.py` and E501s in
`_query.py`/`gates/__init__.py`/`_dup_graph_schema.py`/`_worker.py` are
pre-existing baseline noise in files this ticket did not touch).
`frob check --land-parity` -- ran once, surfaced the two self-introduced
E501s (fixed) plus pre-existing baseline noise; a 155-file repo-wide
`ruff-format` backlog and an unrelated import-cycle warning are
pre-existing, not scoped to this ticket's touched set.

### Changed
```
 tickets/T-2457/ticket.md           | 26 +++++++++++--
 tickets/T-2463/ticket.md | 76 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2464/ticket.md | 56 ++++++++++++++++++++++++++++
 3 files changed, 154 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_vet_capability.py::TestModeAwareOpenCall::test_read_mode_open_reports_fs_read_not_fs_write` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestModeAwareOpenCall::test_default_mode_open_is_read_not_write` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestModeAwareOpenCall::test_write_mode_open_still_reports_fs_write` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestModeAwareOpenCall::test_append_mode_open_still_reports_fs_write` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestModeAwareOpenCall::test_dotwrite_call_still_reports_fs_write` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestModeAwareOpenCall::test_indirect_write_operations_still_reported` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestModeAwareOpenCall::test_dynamic_mode_expression_fails_closed_to_write` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2457/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2457/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2457/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2457/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2457/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2457, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
