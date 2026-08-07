## Done report

Changed:
- src/frob/gates/_secrets.py
- src/frob/gates/__init__.py
- tests/test_secrets_gate.py
- docs/modules/gates.md
- tickets.md

Key decisions:
- SEC003-unwaivable rationale: only live Stripe secret keys (`sk_live_...`) and
  PEM private-key headers are unwaivable, because neither pattern has a
  legitimate "intentionally tracked" reading -- a live Stripe secret key or a
  private-key PEM block committed to a tracked file is a real, exploitable
  leak in every case, unlike JWTs or Stripe test keys, which stay under the
  waivable SEC001 (a JWT can be a test fixture with no real backing account,
  and a Stripe *test*-mode key is by definition not a production credential).
- `frob:secret-fake` naming decision: the existing `frob:secret <id>` DSL
  verb already means something different -- it binds a code site to a strata
  design's Secret-clearance `Node`, consumed by SYS001/SYS002 to prove every
  design secret has a code attestation. Reusing that verb for "this literal
  string is a fake credential" would mint a bogus graph edge and conflate two
  unrelated concerns. Instead a new, non-DSL marker `frob:secret-fake` was
  introduced: matched by plain text scan only, never routed through the DSL
  verb table, never becomes a graph edge.

Evidence: see the evidence list in this ticket's YAML frontmatter above
(tests/test_secrets_gate.py, all classes).

Gates (measured fresh, 2026-07-18, after fixing both findings below for real):
- `frob ticket sweep T-0157`: re-recorded pre-work sweep against current
  scope (dup=155, xref=6) -- clears PRE001, which was a mechanical
  ticket-lifecycle staleness, not a code defect.
- `secrets_gate` branch coverage: a prior pass on this ticket mischaracterized
  its own TEST005 finding (81.2% branch coverage on `secrets_gate`,
  `src/frob/gates/_secrets.py:513`) as "pre-existing, out-of-scope" debt.
  That was wrong -- `secrets_gate` is code this ticket added, so the gap was
  squarely this ticket's own responsibility. Root-caused via coverage.xml
  branch/line inspection to three untested paths inside `secrets_gate`
  itself: (a) the span-claim overlap continue in `_scan_line` (a later,
  less-specific pattern's match nested inside an earlier, more-specific
  pattern's already-claimed span); (b) `_tracked_files`'s `run_argv`
  spawn-error path (`Err(GitError...)`, e.g. `git` missing/timeout); (c) the
  `except (OSError, UnicodeDecodeError)` skip for a tracked binary/unreadable
  file. Added three targeted tests to `tests/test_secrets_gate.py`
  (`TestOverlapClaim`, `TestTrackedFilesGitFailure` x2,
  `TestTrackedEnvFile::test_tracked_binary_file_is_skipped_not_crashed`),
  all runtime-constructed per this file's existing self-match discipline (no
  contiguous 20+ char literal secret-shaped token in the file's own source).
  `secrets_gate` branch coverage is now 100.0% (measured via
  `frob.gates._coverage.load_coverage` against a freshly regenerated
  `coverage.xml`), above the 90% `unit_branch_cov` floor.
- `make coverage` / `uv run pytest --cov=src/frob --cov-branch
  --cov-report=xml`: full pytest suite green under coverage instrumentation
  (exit 0), stamp_coverage stamped 340 files, source_sha=5305e4eb.
- `uv run pytest tests/test_secrets_gate.py`: 47 passed, 0 failed (43
  original + 1 SEC003-waiver-inert regression + 3 new coverage-closing
  tests).
- `uv run frob check --ticket T-0157`: exit 0, gates report 0 violation(s),
  343 waived (unchanged, pre-existing repo-wide waivers unrelated to this
  ticket). Fully clean.
- `uv run frob sys audit`: exit 0 -- PROVED. Checked 8 views
  (security:owasp-top-10, quality:web-performance-baseline,
  quality:reliability-baseline, quality:web-quality-security-baseline,
  compliance:all-regulations, compliance:us-coppa, compliance:eu-gdpr,
  compliance:us-hipaa); selfconform 0 violations; "zero gaps across every
  configured view"; self-conformance "PROVED -- zero SYS gaps".

Filed: none
