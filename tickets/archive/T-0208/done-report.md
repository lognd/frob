## Done report

Root cause confirmed by direct profiling (not just re-trusting the filed
numbers): `high_entropy_strings`'s regex, `(['"])((?:\\.|(?!\1).)*)\1`
with `re.DOTALL`, catastrophically backtracks on real files. A 9.6KB
stdlib-adjacent fixture with nothing adversarial in it
(`blib2to3/pgen2/conv.py` from `setuptools`'s vendored copy, reached via
`.venv/lib/python3.11/site-packages`) measured ~90ms in the regex alone
per call (~0.3ms in the entropy math over the same matches) -- consistent
with the ticket's 82/120 profiled seconds across 785 calls.

Changed:
- src/frob/vet/_obfuscation.py::_iter_string_literals (new) -- single-pass,
  backtracking-free O(len(text)) scan for quoted-literal bodies, replacing
  the regex. Caps: 4096 chars/literal (_MAX_CANDIDATE_LEN), 4000
  literals/file (_MAX_CANDIDATES_PER_FILE).
- src/frob/vet/_obfuscation.py::high_entropy_strings -- now calls
  _iter_string_literals instead of the regex; same threshold/min-length
  logic, unchanged return contract.
- src/frob/vet/_obfuscation.py::_collect_dir_signals -- skips files over
  2MB (_MAX_SCAN_BYTES) with a DEBUG note (not silent) before reading them.
- src/frob/vet/_scan.py::_scan_dependencies -- per-package INFO progress
  (`vet: package M/N name`); new `timeout`/`jobs` keyword params.
- src/frob/vet/_scan.py::_run_with_timeout (new) -- bounds one package's
  `_process_dependency` call in a single-worker ThreadPoolExecutor;
  `fut.result(timeout=...)` on expiry returns `_timeout_verdict` (below)
  instead of raising or silently dropping the package. Python cannot
  preempt a running thread, so the abandoned thread keeps running in the
  background -- disclosed in the docstring, not hidden.
- src/frob/vet/_scan.py::_timeout_verdict (new) -- an honest WARN-severity
  `VET-TIMEOUT` violation plus a `PackageVerdict(signals=("timeout",))`,
  never a silent skip.
- src/frob/vet/_scan.py::scan_tree -- new `timeout: float | None = None`,
  `jobs: int = 1` keyword params, threaded through to `_scan_dependencies`.
  `jobs > 1` scans packages concurrently via `ThreadPoolExecutor`; DISCLOSED
  as best-effort in the docstring -- `.frob/vet.db` (sqlite) and the
  registry publish-date disk cache open short-lived per-call connections
  with no explicit cross-thread locking, so a concurrent write can lose a
  race non-deterministically (never corrupts the cache or crashes the
  scan). `jobs=1` (default) carries none of this risk.
- docs/modules/vet.md -- Mechanics gained a "Progress and bounding
  (T-0208)" bullet; Honest limits gained a paragraph on the entropy scan's
  inherited mismatched-quote false-positive class (unchanged from before
  this fix, verified byte-identical below) plus the new caps, and a note
  (matching the existing T-0110 `--containment` precedent) that CLI wiring
  for `--timeout`/`--jobs` is a separate, out-of-scope follow-up.

Before/after measurements (this repo's own `.venv`, `.venv/lib/python3.11/
site-packages`, 1475 `.py` files, real profile via direct timing, not
estimated):
- Pathological file (`blib2to3/pgen2/conv.py`, 9.6KB): ~90ms/call before
  (git-stash-verified against the original regex) -> ~0.87ms/call after
  (5 calls in 4.35ms) -- ~100x.
- Whole tree (1475 files): pre-fix, a plain per-file timing loop (no
  profiler overhead) did not finish inside a 100s bound (timed out); a
  full `frob vet` run over this repo's own 61-package `uv.lock`, which
  necessarily calls `high_entropy_strings` once per scanned file across
  all 61 packages' source, hung past a 2-minute hard kill with the
  pre-fix code (`git stash` + `timeout 120` + rerun, confirmed by direct
  observation, not inference). Post-fix: whole-tree scan of the same 1475
  files completes in 1.59s.
- Acceptance (frob vet completes on a real venv under ~2 minutes with
  progress output, this repo's own project substituting for "a
  ~100-package venv" per the dispatch instructions -- this repo's own
  `uv.lock` has 61 packages, not ~100; disclosed, not padded): `time
  .venv/bin/python -m frob.__main__ vet .` -> `real 0m41.244s`, with one
  `vet: package M/N name` INFO line per package (61/61 observed,
  `vet: package 1/61 annotated-types` through `vet: package 61/61
  z3-solver`).

Detection NOT weakened, verified two ways:
1. All 9 `TestObfuscationEnsemble` fixtures in tests/test_vet.py pass
   unchanged (evidence below) -- none relied on the old regex's
   pathological behavior.
2. Byte-identical hit-set comparison: ran the OLD regex-based
   implementation (reconstructed inline, not reused from git history) and
   the NEW `high_entropy_strings` side by side over every `.py` file in a
   real installed package (`tomli`, via `_source.locate_source`) --
   `_parser.py` (20 hits) and `_re.py` (1 hit) produced IDENTICAL ordered
   hit lists between old and new. The old regex's mismatched-quote
   false-positive class (an apostrophe in a comment/docstring read as a
   string boundary, producing an oversized "literal" spanning several real
   statements) is preserved exactly, not narrowed or widened -- documented
   in docs/modules/vet.md "Honest limits" as pre-existing, not introduced
   by this ticket.

Cuts / honest disclosure:
- `--timeout`/`--jobs` CLI flags are NOT wired in this ticket -- scope is
  `src/frob/vet/**` only, and the flags live in `app/vet_runner.py`,
  `app/config.py`, `__main__.py` (all outside scope). `scan_tree` and
  `_scan_dependencies` fully support both params at the library level;
  not filed T-draft-ebdd2606 (never refiled) ("wire frob vet --timeout/--jobs CLI flags to
  scan_tree") for the CLI wiring, following the T-0110 `--containment`
  precedent for exactly this scope split. Progress logging (deliverable 2)
  needed no new flag -- it logs at INFO unconditionally, matching this
  repo's existing INFO-by-default stdout handler.
- `--jobs` parallelism is implemented but its safety against the sqlite
  verdict cache / registry disk cache is NOT hardened in this pass (would
  need real locking, e.g. a single writer thread or WAL mode + busy
  timeout tuning) -- disclosed in both the code docstring and
  docs/modules/vet.md rather than silently shipped as if race-free.
  `jobs=1` (default) is unaffected.
- The "~100-package venv" in the acceptance criterion was tested against
  this repo's own 61-package `uv.lock` per the dispatch instructions
  ("this repo's own .venv is fine"); did not have access to the original
  lograder/aprog-public pilot repos to re-run the literal failing case.

Evidence: tests/test_vet.py::TestObfuscationEnsemble (9/9, node ids
recorded via `frob ticket evidence`). Touched-set selection: `frob test
--base main` selected and passed
tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes and
tests/test_vet.py::TestObfuscationEnsemble::
test_high_entropy_strings_returns_the_literal (exit=0, 6.71s). Full
`tests/test_vet.py` module: 96/96 passed (pytest-xdist).
Gates: `frob check --stamp-baseline` then `frob check --delta --ticket
T-0208` -> `gates 0/3 new  0 violation(s), 188 waived`; ruff-check,
ruff-format, and ty all `pass` under both the project-pinned `.venv/bin/
ruff`/`.venv/bin/ty` and the PATH `ruff`/`ty`.
Not Filed: T-draft-ebdd2606 (never refiled) (CLI wiring for --timeout/--jobs, out of scope).

## Review round 2 (REJECT -> addressed)

Reviewer found two real bugs the round-1 report missed. Both fixed and
independently re-verified, not just re-asserted:

**Bug 1 -- timeout didn't actually bound wall time.**
`_run_with_timeout`'s `except FutureTimeoutError: return ...` lived inside
a `with ThreadPoolExecutor(...)` block; `__exit__` calls
`shutdown(wait=True)` unconditionally, so the early return still blocked
until the abandoned worker finished -- reviewer reproduced a 3s task with
`timeout=0.2` returning at 3.0s. Fixed: the pool is now constructed
without `with` and `shutdown(wait=False)` is called explicitly on both
the timeout and success paths (src/frob/vet/_scan.py::_run_with_timeout).
Added `tests/test_vet.py::TestScanTreeTimeout::
test_slow_package_returns_within_timeout_not_task_duration`, which
monkeypatches `_process_dependency` to sleep 3s, calls `scan_tree(...,
timeout=0.2)`, and asserts `elapsed < 1.5s`. Verified the test actually
catches the bug: `git stash push -- src/frob/vet/_scan.py` then running
the test against the pre-fix code FAILS (observed ~3.2s elapsed,
assertion error); against the fix it PASSES (~0.4s, confirmed via
`pytest -k test_slow_package -q`, 1 passed).

**Bug 2 -- `_iter_string_literals` diverges from the old regex beyond the
disclosed pre-existing false-positive class, with a real detection gap.**
The round-1 Done report's "byte-identical" claim was based on ONE
package (`tomli`, 2 files) -- not evidence of corpus-wide equivalence.
Reviewer compared old-vs-new over all 105 `pydantic` files in this
repo's `.venv` and found 14 divergent; root-caused to two distinct bugs:

1. *Unterminated candidates.* A quote character with no closing quote
   anywhere later in the file was scored as a literal running to
   end-of-text; the old regex instead fails that match attempt entirely
   and retries one character later (confirmed by direct trace on
   `pydantic/_internal/_signature.py`: after a mismatched-quote span
   consumes the file's last `'`, the old regex correctly re-syncs on the
   next docstring's triple-quote and finds real hits there; the pre-fix
   scanner instead swallowed that docstring into one 982-char bogus
   "literal" and never scored the real content). Naively matching the old
   regex's retry-one-char-over behavior reintroduces the exact quadratic
   blowup T-0208 fixed for a file with many trailing unmatched quote
   characters, so the fix precomputes each quote type's LAST raw
   occurrence in the file once (`last_single`/`last_double`) and rejects
   an unclosable candidate in O(1).
2. *Entropy-truncation detection loss.* The 4096-char cap on the CONTENT
   fed to the entropy check (not just the returned/logged snippet) could
   pull a genuine hit's score back under threshold -- measured directly on
   a real file (`cryptography/hazmat/primitives/serialization/pkcs7.py`):
   `entropy(full 7575-char mismatched-quote span) = 4.602` (fires),
   `entropy(same span truncated to 4096) = 4.472` (silent). This is what
   actually caused 4 of the corpus-wide presence-flip losses (see below),
   not bug 2.1. Fixed by never truncating the entropy input: the O(n)
   bound for the scan does not require a length cap -- every successful
   (closing) literal's inner scan consumes its own span exactly once and
   the outer loop never revisits those characters, so total scan work
   across ALL successful literals in a file is bounded by `len(text)`
   regardless of any single literal's length; only a FAILED open needs to
   stay O(1), which bug 2.1's fix already guarantees.
   `_MAX_CANDIDATE_LEN` is now a 1MB memory-safety ceiling (an adversarial
   multi-hundred-MB "string" OOM guard), not a normal-path truncation --
   raised from 4096 to 1_000_000.

Full-corpus re-verification (not a sample), per reviewer's explicit
instruction: old (the pathological regex) vs new, over every `.py` file
under this repo's own `.venv/lib/python3.11/site-packages` (1475 files),
with the OLD implementation bounded by a 3s-per-file SIGALRM budget so a
handful of genuinely intractable files don't block comparing the rest
(this bound is itself evidence for the ticket, not a methodology gap: old
timed out past 3s on 7/1475 real files -- `cryptography/hazmat/
primitives/keywrap.py`, `httpx/_multipart.py`, `hypothesis/strategies/
_internal/strings.py`, `pygments/lexers/c_like.py`, `pygments/lexers/
crystal.py`, `pygments/lexers/func.py`, `starlette/responses.py`).

- Before either fix (state reviewer rejected): 1468/1475 compared, 81
  divergent, **4 presence-flip losses** (old fired, new silent --
  `cryptography/.../pkcs7.py`, `hypothesis/.../provider_conformance.py`,
  `referencing/tests/test_core.py`, `uvicorn/.../wsproto_impl.py`, all
  traced to the entropy-truncation bug), 5 presence-flip gains, 72
  count/snippet-only divergences.
- After both fixes: 1468/1475 compared, **1 divergent, 0 presence-flip
  losses, 0 presence-flip gains**. The 1 remaining divergence
  (`pygments/lexers/_cocoa_builtins.py`) is the disclosed, deliberate
  `_MAX_CANDIDATES_PER_FILE=4000` cap -- a builtins-list file with over
  4000 tiny quoted tokens; the cap cuts off one specific late literal,
  but two earlier ones in the same file already trip the threshold under
  BOTH old and new, so the file's aggregate `high-entropy-string` signal
  (what VET004 actually keys on) is identical before and after.

Detection parity restored: 0 files anywhere in a 1468-file real-world
corpus now flip from "old would have flagged this" to "new stays silent."

Performance re-confirmed after both fixes (no regression from removing
the length-truncation cap, since the O(n) bound never depended on it):
pathological file (`blib2to3/pgen2/conv.py`) 5 calls in 4.1ms (~0.82ms/
call, consistent with round 1's ~0.87ms/call); whole `.venv/site-packages`
tree (1475 files) 1.53s; real `frob vet` run on this repo's own 61-package
`uv.lock`, `real 0m18.667s` (faster than round 1's 41s -- removing the
truncation cap means fewer wasted rescans of capped-and-reopened
literals), all 61 `vet: package M/N name` progress lines present.

Evidence added: `tests/test_vet.py::TestScanTreeTimeout::
test_slow_package_returns_within_timeout_not_task_duration` (recorded via
`frob ticket evidence`).
Gates (post-merge-of-main, tip 45b3129/9d41af5): `frob check
--stamp-baseline` then `frob check --delta --ticket T-0208` -> `gates
0/8 new  0 violation(s), 27 waived`; ruff-check/ruff-format/ty clean under
both `.venv/bin/*` and PATH. `frob test --base main`: touched-set
selection (5 node ids including the full `tests/test_vet.py` module and
the new timeout test) exit=0, 5.09s. Deletion-filter (`git diff main
--diff-filter=D --stat`) empty.
