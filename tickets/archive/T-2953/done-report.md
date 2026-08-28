## Done report

Changed:
src/frob/process/_guard.py::guarded_subprocess_run
src/frob/process/_guard.py::_default_text_encoding
src/frob/serve/_socketd.py::_source_head_sha
src/frob/app/_daemon_proxy.py (private source-sha helper)
src/frob/app/ticket_runner/_land_cmd.py::_run_ty
src/frob/app/ticket_runner/_close_cmd.py::_current_commit
src/frob/app/ticket_runner/_rapid_sweep.py (auto-drop git-checkout restore)

Sweep inventory (measured, before fixing): AST-based scan of src/ for
the whole class of platform-locale-codec text decoding: subprocess.run/
Popen/check_output/check_call calls with text=True or
universal_newlines=True and no explicit encoding=; bare .decode() with
no arguments; open() without encoding= (non-binary mode); Path.read_text
/write_text without encoding=. Found:
  - subprocess text-mode, no encoding=: 5 raw call sites (all fixed
    below), plus guarded_subprocess_run itself (the seam most other
    subprocess.run(text=True, ...) callers in this repo already route
    through -- fixing it there closes the class for every one of THOSE
    callers in one place, without a per-call-site diff).
  - bare .decode(): 0 sites repo-wide.
  - open()/read_text/write_text without encoding=: 20 + 44 sites,
    almost all operating on this repo's own ASCII-only tracked content
    (ticket files, lock files, cache JSON) rather than third-party tool
    output. NOT fixed in this ticket -- out of the class this ticket's
    acceptance criteria (get past `make core`/`ty check`) actually
    needed, and fixing 64 sites on spec without a concrete crash to
    verify against would be exactly the "fix what I imagine" mistake
    this chain's own discipline exists to avoid. Left as an inventoried,
    unconfirmed-risk count; not filed as a ticket since no crash from
    this sub-class has been observed on real CI.

Fix: guarded_subprocess_run (src/frob/process/_guard.py) now runs every
kwargs dict through _default_text_encoding, which injects
encoding="utf-8", errors="replace" whenever text=True/
universal_newlines=True was requested and no encoding= was given --
covers every CURRENT and FUTURE caller of this seam (confirmed:
_land_cmd.py/_close_cmd.py/_rapid_sweep.py's OWN guarded_subprocess_run
call sites needed no per-site change at all). The 5 raw
subprocess.run(text=True, ...) sites outside the seam
(_socketd.py::_source_head_sha, _daemon_proxy.py's twin, _land_cmd.py's
_run_ty, _close_cmd.py's _current_commit, _rapid_sweep.py's auto-drop
restore) were fixed directly with the same encoding="utf-8",
errors="replace" pair. errors="replace" (not "strict") chosen
deliberately: a garbled byte inside captured diagnostic text is a real,
survivable degradation (a `�` in a log line); an unhandled
exception before the diagnostic is even returned to the caller is not.

Evidence:
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_injects_utf8_replace_when_text_true_and_no_encoding
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_injects_when_universal_newlines_true
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_never_overrides_explicit_encoding
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_never_overrides_explicit_errors
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_no_op_without_text_mode
- tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_guarded_subprocess_run_survives_the_reported_crash_byte

check-repro was not used: same platform-absence reasoning as T-2952 --
this crash only occurs under the Windows locale codec, unreproducible
as a FAILED_AT_PARENT node on Linux CI. Evidence instead follows the
T-2936/T-2952 precedent: a regression test that reproduces the EXACT
reported byte (0x8f, the literal byte windows-latest CI's
UnicodeDecodeError named) through the real guarded_subprocess_run path
end-to-end, confirming it no longer raises and the captured stdout is a
real str (never None, which is what crashed the downstream pydantic
CrateBuildResult model), plus unit coverage of the injection helper's
every branch, plus a REAL windows-latest CI run as the actual
acceptance evidence (below).

Real windows-latest CI run: https://github.com/lognd/frob/pull/3, run
32941580418, job 98093462106 (commit 341022b88, after the E501-fix
follow-up commit needed because the FIRST push of this fix carried a
ruff-check regression of its own -- long frob:tests directive lines --
caught by this same PR's CI on all three platforms and fixed before
this run). Confirmed: `make core` (frob natives build, including its
maturin/cargo subprocess calls) completed cleanly, no
UnicodeDecodeError anywhere in the log. `ruff check`/`ruff format` both
passed. The pipeline reached `uv run ty check src` -- substantially
further than T-2953's own parent measurement (which stopped at `make
core`) and than T-2952's (which stopped at the fcntl import).

`ty check` then failed with 6 diagnostics, all one new, distinct class:
POSIX-only stdlib attributes (socket.AF_UNIX x3,
socketserver.ThreadingUnixStreamServer, os.nice) that do not exist in
typeshed's Windows view of the standard library. This is NOT a decode
crash and NOT an import crash -- it is the next thing in the chain, as
expected. Filed as T-2961 (renumbers at land) per this
chain's own directive; NOT fixed here.

(a) Does frob IMPORT on Windows? YES (unchanged from T-2952; this
ticket did not touch import-time behavior).

(b) Does frob RUN USEFULLY on Windows? Still NO, but measurably closer:
`frob natives build` (make core) now completes successfully on
windows-latest CI, including its native Rust extension build -- the
single most load-bearing step in the whole pipeline (every downstream
frob check/frob test call needs it). The pipeline now dies at `ty
check`, a static analysis gate, not a runtime crash -- meaning the
CODE that ty is refusing to typecheck (the socket-daemon/verify-worker
modules) has not yet even been proven to RUN on Windows; ty is
correctly reporting that these modules reference symbols the Windows
standard library does not have, which is orthogonal to whether the
rest of frob (tickets, gates, check machinery) would work once this
gate is satisfied. Filed T-2961 rather than guessing at a
fix; the next agent's CI run will show whether clearing ty gets frob
running usefully or reveals crash #5.

Filed: T-2961 (Windows ty-check POSIX-only stdlib attrs:
socket.AF_UNIX, socketserver.ThreadingUnixStreamServer, os.nice --
unrelated defect discovered via the real CI run this ticket's
acceptance criteria required)

Gates: `frob check --ticket T-2953 --only affect_drift --only scope
--only fmt` clean (0 errors, only pre-existing advisory SCOPE002
warnings from touching a central seam many symbols transitively
depend on). Also self-corrected a ruff-check E501 regression the
initial commit introduced (long frob:tests directive lines), caught by
this PR's own CI before the acceptance-criteria CI run.

### Changed
```
 docs/modules/process.md                    |  11 +++
 docs/modules/serve.md                      |   7 +-
 src/frob/app/_daemon_proxy.py              |   2 +
 src/frob/app/ticket_runner/_close_cmd.py   |   2 +
 src/frob/app/ticket_runner/_land_cmd.py    |   9 +-
 src/frob/app/ticket_runner/_rapid_sweep.py |   2 +
 src/frob/process/_guard.py                 |  35 +++++++
 src/frob/serve/_socketd.py                 |   2 +
 tests/unit/test_process_guard.py           |  62 ++++++++++++
 tickets/T-2953/done-report.md              | 143 +++++++++++++++++++++++++++
 tickets/T-2953/ticket.md                   | 150 ++++++++++++++++++++++++++++-
 tickets/T-2961/ticket.md         |  94 ++++++++++++++++++
 12 files changed, 515 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_injects_utf8_replace_when_text_true_and_no_encoding` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_injects_when_universal_newlines_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_never_overrides_explicit_encoding` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_never_overrides_explicit_errors` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_no_op_without_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestDefaultTextEncoding::test_guarded_subprocess_run_survives_the_reported_crash_byte` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 26 error(s), 1047 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PRE001@tickets/T-2953, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
