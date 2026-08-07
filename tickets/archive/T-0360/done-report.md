## Done report

Changed:
- src/frob/arch/_python.py::_is_dispatch_family (new)
- src/frob/arch/_python.py::_check_abstraction_opportunities (now takes `all_texts`, skips dispatch families)
- src/frob/arch/__init__.py::_analyze_one_file (accumulates decoded source text per file)
- src/frob/arch/__init__.py::analyze_project (threads `all_texts` through to `_check_abstraction_opportunities`)
- docs/modules/arch.md (new "abstraction-opportunity excludes intentional dispatch families (T-0360)" section)

Detector change: `_is_dispatch_family` recognizes an intentional dispatch/
validator family via a text-proximity heuristic (no full call graph needed
at `frob.arch`'s stage): two same-signature group members are "linked" if
some single source file mentions both names at least twice each (the
`def` plus at least one more reference -- a registry dict, an `elif`
chain, an import-and-call). A group is suppressed when every member is
linked to at least one sibling (a large family may be served by more than
one such site, e.g. two separate command tables colliding on signature);
a group with an unlinked member still flags.

Before/after (measured, `uv run frob check --only arch 2>&1 | grep -c
abstraction-opportunity`): 97 -> 47 (52% drop). Residual 47 were reviewed
by category:
- Suppressed as intentional dispatch families (detector, no code change
  needed beyond the above): the AppConfig `_run_*` handler tables in
  `app/gitlog_runner.py`, `app/ticket_runner.py`/`app/vet_runner.py`'s
  shared-signature split, `strata/_breach.py`/`_facts.py`/`_elaborate.py`
  validator runners, `strata/_claims.py` bound-claim evaluators, and
  several `check/_python.py` `_run_*` tool dispatchers, among others --
  see the delta (50 findings) between the 97-before and 47-after lists.
- Left flagged (genuine residue, reviewed, not waived): groups like
  `excludes.py`'s 30-function `(str) -> bool` group, `gates/__init__.py`'s
  31-function `(str) -> str` group, and similar large heterogeneous
  groups are NOT one dispatch/validator family -- they are unrelated
  helper functions that happen to share a common, generic Python
  signature shape (a predicate or a string transform) with no common
  registry/call site anywhere in the tree. These stay flagged as honest,
  if low-priority, advisory suggestions.
- NOT disposed via `frob:waive`: `abstraction-opportunity` is one of
  `frob.gates._unwaivable_channel_rules`'s categories (T-0101 decision) --
  a `frob:waive abstraction-opportunity reason="..."` directive can never
  reach this category and would itself be flagged as an ineffective
  waiver. The only lever for this category is the detector (done above)
  or fixing the code (extracting a real shared abstraction, out of scope
  for a disposition-only ticket). This is disclosed here rather than
  silently working around it with waivers that would not actually take
  effect.

Tests added (tests/unit/test_arch.py, class `TestDispatchFamilySuppression`):
- test_dispatch_family_no_abstraction_opportunity -- three same-signature
  handlers registered in one command table in the same file: no
  abstraction-opportunity.
- test_accidental_same_signature_still_flagged -- three same-signature
  functions in three separate files with no common caller anywhere: still
  flags, and the message names all three functions.

Evidence:
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_accidental_same_signature_still_flagged
- `uv run pytest tests/unit/test_arch.py -q -p no:cacheprovider` -- 24 passed
  (all of test_arch.py, including the two new tests above).
- `uv run frob check --only arch 2>&1 | grep -c abstraction-opportunity` --
  97 before this change, 47 after (measured, not estimated).

Filed: none (no out-of-scope work found; the ticket's own scope covers
both the detector file and src/frob/**).

Gates: `uv run frob check --only arch` runs clean (exit 0, arch stage is
advisory/non-gating). A full `uv run frob check --ticket T-0360` was
started but is slow in this environment (~200s sys/secrets/tickets
stages under the /mnt mount tax, per coordinator guidance) and was not
waited on to completion in this pass; the fast, targeted arch-stage and
touched-test verification above is what this Done report's numbers are
based on. Coordinator to re-verify full `frob check` at land.

## Round 2: reviewer-required fix (structural, not textual, linking)

Reviewer REJECTED round 1: the `>=2 textual mentions in one file` linking
signal demonstrably false-suppressed genuine findings with zero real
dispatch signal -- (1) a package `__init__.py` re-export (`from .a import
name` + `name` listed in `__all__`) mentions a name twice with no
dispatch involved, and (2) a test file that imports and calls three
unrelated same-signature functions also mentions each name twice via
ordinary test assertions. Both fully suppressed a real
abstraction-opportunity finding.

Fix: `_is_dispatch_family`'s linking signal is now STRUCTURAL, off the
existing tree-sitter parse, not textual. New
`src/frob/arch/_python.py::collect_file_dispatch_refs` (public,
docstring-documented) walks a file's tree and records a name only when it
appears in one of four dispatch-shaped positions: the callee of a `call`,
a positional/keyword argument of a `call`, a value inside a `dictionary`
literal's `pair`, or an element of a `list`/`set`/`tuple` literal. A bare
import, a docstring mention, or a string in `__all__` matches none of
these and no longer counts. Two additional exclusions, defense-in-depth
on top of the structural-only signal:
`src/frob/arch/__init__.py::_is_init_file` drops `__init__.py` files from
the corpus outright, and the existing `is_test_file` check (already used
for T-0359's advisory-category test exemption) now also gates whether a
file's dispatch references are added to the corpus at all, not just
whether the file itself gets flagged.

Adversarial tests added (both reproduce the reviewer's two exploits and
now pass): `TestDispatchFamilySuppression::test_init_reexport_does_not_suppress`
(three unrelated same-signature functions re-exported through an
`__init__.py` with `__all__` -- still flags) and
`::test_test_file_co_mention_does_not_suppress` (three unrelated
same-signature functions imported and called from one test file -- still
flags). The original true-positive (`test_dispatch_family_no_abstraction_opportunity`,
a real dict-literal command table -- suppressed) and true-negative
(`test_accidental_same_signature_still_flagged`, three functions with no
common site anywhere -- still flags) tests are unchanged and still pass.

Verification (fast path only, per coordinator instruction, not the slow
full `frob check`):
- `uv run pytest tests/unit/test_arch.py -q -p no:cacheprovider -o
  addopts=""` -- 26 passed, including both new adversarial tests.
- `uv run frob check --only arch 2>&1 | grep -c abstraction-opportunity`
  -- 97 (pre-T-0360) -> 67 (post-fix). The stricter structural check
  correctly suppresses fewer groups than the buggy textual heuristic did
  (67 vs the round-1 report's 47) -- that drop in suppressions is the
  fix working as intended, not a regression: the round-1 47 included the
  two false-suppression classes the reviewer demonstrated.
- `uv run ruff check` / `uv run ruff format --check` on the touched files
  -- clean. `uv run ty check src/frob/arch/` -- clean.
- `git diff main --diff-filter=D --stat` after `git merge main` -- empty
  (no unintended deletions; `main` had advanced with two new coverage
  test files that a naive stale-base merge could have dropped, but the
  merge picked them up correctly).

Evidence added: `TestDispatchFamilySuppression::test_init_reexport_does_not_suppress`,
`::test_test_file_co_mention_does_not_suppress` (4 total evidence ids on
the ticket now).

Filed: none.
