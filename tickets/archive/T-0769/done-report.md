## Done report

## Done report

Root cause (two distinct instances of the same class):

1. Set-level scan (`src/frob/vet/_capability.py::scan_file_capabilities` /
   `_scan_file_operations` / `_scan_file_fingerprints`): the raw-text
   needle scan excluded tree-sitter COMMENT spans (T-0209) but never
   computed or excluded python DOCSTRING string-literal spans, so needle
   prose written in a module/class/function docstring (e.g.
   `_concurrency.py`'s fork/pool-hazard documentation literally spelling
   `subprocess.Popen(...)`/`os.fork()`) was observed as a real capability.

2. Line-level scan feeding THREAT004/`check_capability_conformance`
   (strata's SYS100 selfconform delegate): `src/frob/strata/_effects.py::
   _needle_matches`/`_line_effects` did its own raw `needle in line`
   substring scan with **zero** comment-or-docstring awareness at all --
   it never consulted `frob.vet._capability`'s span machinery in any form.
   This is the actual mechanism behind the reported `_concurrency.py:56`
   false positive (prose inside a `#:` COMMENT, not just a docstring).

Fix: `_docstring_byte_spans` (new, `_capability.py`) computes python
module/class/function-head docstring spans the same way `_comment_byte_
spans` computes comment spans; `_non_executable_byte_spans` unions the
two, and every raw-text scan call site in `_capability.py` that used to
pass comment-only spans now passes the union. A new public primitive,
`non_executable_line_numbers(path)`, exposes the same span computation as
1-indexed line numbers; `_effects.py::_needle_matches`/`_line_effects` was
updated (ticket scope expanded, see below) to skip any line that
primitive reports, closing instance 2 with the same span computation
instance 1 uses -- binding-aware resolution (T-0328/T-0337/T-0377/T-0378/
T-0379) is untouched.

While fixing this, `_effects.py`'s OWN module docstring turned out to
contain a `requests.post(...)`-shaped example that its own `net` needle
table matched -- a second, self-inflicted instance of the exact class
this ticket fixes, uncovered only once the fix was in place (confirmed by
reverting the two source files to `main` and re-running the failing
selfconform test, which passes there). Reworded in place, mirroring the
T-0695 `_concurrency.py` mitigation precedent.

Changed:
- src/frob/vet/_capability.py :: `_docstring_byte_spans`,
  `_py_leading_docstring_node`, `_non_executable_byte_spans`,
  `non_executable_line_numbers` (new); `scan_file_capabilities`,
  `_scan_file_operations`, `_scan_file_fingerprints` now source spans from
  `_non_executable_byte_spans` instead of `_comment_byte_spans` alone
- src/frob/strata/_effects.py :: `_needle_matches`, `_line_effects` (now
  comment/docstring-aware via `non_executable_line_numbers`); module
  docstring reworded to remove its own accidental `net` needle match
- tests/test_vet_capability.py (new) :: set-level and line-level
  regression coverage, both the prose-only negative case and a real-exec
  positive control
- tests/test_vet.py :: `TestCapabilityScan::
  test_capability_module_self_scan_documented_false_positive` updated --
  the "cmdclass"/"install-hook" instance of the locked false-positive
  class no longer applies post-fix (it was docstring-only); relocked
  against the `_has_bare_compile_call` code-data instance, which still
  holds
- docs/modules/vet.md :: added the `frob:describes` anchor + Public API
  prose entry for `non_executable_line_numbers` (reviewer-found gap, see
  addendum below)
- design/frob.strata :: removed the stale `may "net";` atom (and its now-
  dead T-0174 LINT004 waiver) from the `stratamod` node (coordinator-
  directed fold, see addendum below)

Evidence (bound to acceptance index 0):
- tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_docstring_and_comment_prose_yields_no_exec_capability
- tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_real_exec_call_still_observed
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_prose_only_lines_report_zero_exec_observation_via_selfconform
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_real_exec_call_still_flagged_via_selfconform
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_covers_docstring_and_comment
- tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
- `uv run frob test --base main`: run_selected python exit=0 (includes the
  full `tests/test_vet.py` + `tests/test_vet_capability.py` +
  `tests/test_capability_registry.py` + `tests/system/test_cli_vet.py`
  touched-set)
- `uv run pytest tests/test_vet_capability.py tests/test_vet.py
  tests/unit/strata/test_effects.py -q`: 138 passed
- `uv run --frozen pytest tests/unit/strata/test_selfconform.py -q`: 43
  passed (post-narrowing; `TestRealGateGreen` now green for real, not via
  a masked false positive)

Scope changes (with reasons, via `frob ticket scope --add
--reason-file`/`--reason`):
- `src/frob/strata/_effects.py` + `tests/unit/strata/test_effects.py`:
  the ticket body explicitly required root-causing BOTH raw-text
  observation paths, and the line-level one lives here
- `tests/test_vet.py`: the fix directly falsifies one locked assertion in
  this file (`test_capability_module_self_scan_documented_false_
  positive`); had to be updated in the same change, not left red
- `docs/modules/vet.md`: reviewer-found COV001 debt -- the new
  `non_executable_line_numbers` symbol carried a `frob:doc` anchor with
  no corresponding doc entry
- `design/frob.strata` + `tests/unit/strata/test_selfconform.py`:
  coordinator-directed land-together fold, see Deviation below

Gates: `uv run frob check --ticket T-0769 --only lint` clean; `--only
static` PASS (frob-exports warnings are pre-existing repo-wide, unrelated
to this change); `--only gates-fast` clean except a transient `uv.lock`
diff that every `uv run` invocation in this checkout re-introduces on its
own (pyproject.toml's 0.98.0 vs the checked-in lock's stale 0.97.0
embedded-package line -- `git checkout -- uv.lock` before finishing,
matches the documented land-owned-files rule, section 4b of the agent
playbook; not committed) and two pre-existing TEST010 findings from
main's own merged-in tickets, unrelated to this change; `--only
gates-native` clean; `--only gates-security` clean. `gate:DOC 0 errors`
and `gate:COV 0 errors` confirmed clean for the new doc entry. No
DRIFT001 fired for the new ref, so `frob ack` was not required.

Deviation 1: ticket scope as originally declared
(`src/frob/vet/_capability.py`, `tests/test_vet_capability.py`) covered
only the set-level half; the ticket BODY explicitly demanded both, so
scope was extended per the process (see above) rather than silently
leaving the line-level THREAT004 path unfixed.

Deviation 2 (doc-anchor fix): reviewer found `non_executable_line_
numbers` carried a `frob:doc docs/modules/vet.md#public-api` anchor with
no corresponding doc entry (COV001 debt). Fixed in-worktree: added the
`frob:describes` anchor plus a Public API prose entry; scope extended to
`docs/modules/vet.md` with a recorded reason. `gate:DOC`/`gate:COV` both
confirmed 0 errors afterward.

Deviation 3 (SYS101 fold, coordinator-directed): on coordinator
instruction, the T-draft-22aa6efc follow-up (stratamod's stale `may
"net"` declaration, uncovered by this ticket's own fix -- see the
original Filed note below, superseded) was folded directly into this
worktree rather than landed separately, to avoid a red-`TestRealGateGreen`
window on `main` between T-0769 landing and a follow-up landing. Scope
was extended to `design/frob.strata` + `tests/unit/strata/
test_selfconform.py` (reason recorded via `frob ticket scope --reason`).
The stale `may "net";` atom (and its now-dead T-0174 LINT004 waiver) was
REMOVED from the `stratamod` node -- a strictness-INCREASING narrowing,
not a relaxation: T-0769's own scanner fix proved no code under
`src/frob/strata/**` genuinely exercises net (the only "observation" was
the `_effects.py` docstring false positive this same ticket already
reworded). No real net kill-switch mechanism (T-0200) was built as an
alternative -- narrowing was chosen specifically because there is
currently zero real net-capable code to protect; if `stratamod`
genuinely grows a net-capable call in the future, `may "net"` must be
re-declared then, alongside a real kill switch, not carried forward
speculatively. `T-draft-22aa6efc` was dropped (`--absorbed-by T-0769`)
rather than landed separately. Verified: `uv run --frozen pytest
tests/unit/strata/test_selfconform.py -q` -- 43 passed, zero violations,
`TestRealGateGreen` green for real.

(Original Filed note, now superseded by Deviation 3 above: T-draft-
22aa6efc was filed documenting the stratamod may-net staleness this
ticket's fix uncovers; it is now dropped/absorbed rather than landed
separately.)

### Changed
```
 docs/modules/vet.md          |   7 ++
 src/frob/strata/_effects.py  |  50 ++++++--
 src/frob/vet/_capability.py  | 145 +++++++++++++++++++++-
 tests/test_vet.py            |  18 ++-
 tests/test_vet_capability.py | 122 +++++++++++++++++++
 tickets.md                   | 281 ++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 606 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_docstring_and_comment_prose_yields_no_exec_capability` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_real_exec_call_still_observed` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_prose_only_lines_report_zero_exec_observation_via_selfconform` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_real_exec_call_still_flagged_via_selfconform` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_covers_docstring_and_comment` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive` (pytest node id, verified passing when recorded)
