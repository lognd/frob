## Done report

src/frob/policy/__init__.py::_files_under
src/frob/policy/__init__.py::_compiled_glob (new)
pyproject.toml (pathspec promoted from transitive-via-mypy to a direct dependency)

Evidence:
tests/test_policy.py::TestRules.test_glob_double_star_matches_file_directly_under_prefix (must-fire fixture)
tests/test_policy.py::TestRules.test_glob_stays_quiet_outside_matched_directory (must-stay-quiet fixture)
`frob test --base main`: PASS (4 python test outcomes recorded, exit=0)

Fix: `frob.policy._files_under` now matches policy globs via `pathspec.PathSpec.from_lines("gitignore", [pattern])`
(pathspec's gitwildmatch dialect) instead of `fnmatch.fnmatch`. Confirmed by measurement before fixing:
`fnmatch("app/request_context.py", "app/**/*.py")` -> False (silently misses a file directly under the prefix);
`pathspec` gives True, matching what every author means by `**` (.gitignore/ruff/etc semantics) and is
platform-independent (fnmatch normcase's both sides, so the same pattern matched differently on Windows vs Linux --
pathspec's gitwildmatch dialect does not).

Widening delta measured (THIRD FIXTURE): this repo's own `frob.toml` has NO `[policy]` table at all (`grep -n policy
frob.toml` -> no hits; `frob check --only policy` reports `policy=0.00s`, i.e. 0 rules loaded) -- so the real,
measured before/after delta across this repo's own policy set is 0 -> 0 findings; there is nothing to widen because
no policy rule exists here to widen. The must-fire/must-stay-quiet fixtures above demonstrate the exact defect and
its bounded fix synthetically (0 -> 1 finding for the must-fire case; 0 -> 0, unchanged, for the must-stay-quiet
case) since this repo has no live policy rule to measure the delta against directly.

Eight fnmatch call sites classified (per the ticket's own enumeration):
1. src/frob/policy/__init__.py:40 _files_under -- policy `within`/`globs` from frob.toml, USER-AUTHORED. AFFECTED.
   FIXED in this ticket.
2. src/frob/excludes.py:83 is_excluded -- [graph].exclude globs from frob.toml, USER-AUTHORED. AFFECTED, not fixed
   here (out of T-4013's declared scope).
3. src/frob/gates/__init__.py:543 _glob_prefix_match -- [[system]].paths glob, USER-AUTHORED. AFFECTED, not fixed
   here.
4. src/frob/gates/__init__.py:1443 _scope_glob_specificity -- ticket scope globs (via `_scope_globs`),
   USER-AUTHORED; connects directly to T-3978 (a scope glob matching zero tracked files is accepted silently) --
   an under-matching `**` is one way to produce a zero-match scope. AFFECTED, not fixed here.
5. src/frob/gates/_refs.py:384 _allowlist_covers -- [[refs.entrypoint]] allowlist globs, USER-AUTHORED (uses
   `fnmatchcase`, so already platform-independent on case-sensitivity, but still lacks `**` semantics). AFFECTED,
   not fixed here.
6. src/frob/gates/_doclink_docanchor.py:127 -- docs include/exclude globs, USER-AUTHORED; the file already carries
   a WALK001 waiver comment that itself documents this exact fnmatch `**` gap. AFFECTED, not fixed here.
7. src/frob/app/ticket_runner/_close_cmd.py:402 _matching_gate_claim_files -- ticket-close evidence criterion glob,
   USER-AUTHORED. AFFECTED, not fixed here.
8. src/frob/app/ticket_runner/_query.py:1255 -- ticket scope globs (same `_scope_globs` expansion as #4),
   USER-AUTHORED. AFFECTED, not fixed here.

NOT classified as a user-authored-glob site needing this fix: src/frob/gates/_fix_engine_text.py:362 matches
against ruff's own `per-file-ignores` config specifically to mirror what ruff itself would do -- switching it to
gitwildmatch could DIVERGE from ruff's actual glob dialect rather than fix a bug, so it needs its own investigation
into ruff's matching semantics, not this ticket's fix. Windows-half note (per the T-3947/T-3948 caution in this
ticket's brief): every one of the 7 unfixed sites uses `fnmatch.fnmatch`/`fnmatch.fnmatchcase`/`fnmatch.filter`,
which IS self-correcting on Windows via `os.path.normcase` -- their defect is the missing `**` semantics, not a
genuinely-broken-on-Windows plain string comparison; none of the 8 sites use a bare string-equality/`==` path
comparison that `normcase` would not already compensate for.

Filed: T-4099 (F-226 follow-up) -- scope: src/frob/excludes.py, src/frob/gates/__init__.py,
src/frob/gates/_refs.py, src/frob/gates/_doclink_docanchor.py, src/frob/app/ticket_runner/_close_cmd.py,
src/frob/app/ticket_runner/_query.py. Covers sites 2-8 above (the fix pattern from this ticket, replicated).

T-3986 cross-reference (per this ticket's own ask): T-3986 (F-196's POL000 -- a policy.pattern matching zero nodes
across its whole glob set is "unproven" and reported) is STILL needed after this fix. This ticket fixes ONE cause
of a silent zero-match (fnmatch's missing `**`); T-3986 is the general "prove every policy glob matches at least
one node, whatever the reason it might not" class -- an author's simple typo, a moved/renamed directory, or any
other glob-authoring mistake would still produce a silent zero-match with this fix alone. Not fixed here (T-3986
is its own already-filed ticket).

Gates: `frob check --ticket T-4013` (chunked: gates-fast/gates-native/gates-security/lint/static, per T-0627's
FROB_AGENT full-run restriction) -- clean except:
  - gate:SCOPE SCOPE002 (1): T-4013's scope (src/frob/policy/__init__.py, tests/test_policy.py, pyproject.toml)
    does not include docs/modules/gates.md, which `load_policy`/`policy_gate`'s `frob:doc` anchor targets.
    Adding docs/modules/gates.md to scope closure-explodes into 343 unrelated doc-anchor/symbol warnings (that
    doc file documents nearly the entire gates subsystem) -- same disclosed-breadth class T-3914's and T-4019's
    own Done reports already measured and accepted (`frob:waive SCOPE002 reason="docs/modules/gates.md ...
    cross-documented far beyond this ticket's actual diff ... narrowing would require pulling in most of
    src/frob/gates/** ... for a load-scoping fix ... same disclosed-breadth class as T-3914"`). Disclosed here
    the same way, not suppressed: `frob:waive SCOPE002 reason="docs/modules/gates.md describes nearly the whole
    gates subsystem (343 unrelated doc-anchor/symbol closure warnings when added to scope) for a 2-function
    glob-matching fix that touches src/frob/policy/__init__.py alone; narrowing would require pulling in most of
    src/frob/gates/** -- same disclosed-breadth class T-3914/T-4019 already measured and accepted"`.
  - gate:PERF PERF003 (1) at tests/test_serve_socket.py:347 -- pre-existing, repo-wide, unrelated to this ticket's
    diff (that file is untouched by this change; confirmed via `git diff --stat main` showing zero lines changed
    there by this ticket).
  gate:FMT (FMT001, over-long directive lines) and gate:PRE (PRE001, stale pre-work sweep) were both real and are
  now fixed (directive lines rewrapped via `frob format --directives`; `frob ticket sweep T-4013` re-run).

`frob test --base main`: PASS (see Evidence above).

### Changed
```
 pyproject.toml                     |   7 +++
 src/frob/policy/__init__.py        |  31 +++++++++--
 tests/test_policy.py               |  44 ++++++++++++++++
 tickets/T-4013/done-report.md      | 102 +++++++++++++++++++++++++++++++++++++
 tickets/T-4013/ticket.md           |   3 ++
 tickets/T-4099/ticket.md |  47 +++++++++++++++++
 6 files changed, 231 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_policy.py::TestRules::test_glob_double_star_matches_file_directly_under_prefix` (pytest node id, verified passing when recorded)
- `tests/test_policy.py::TestRules::test_glob_stays_quiet_outside_matched_directory` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 4423 warning(s), 931 waived
- error-findings: PERF003@tests/test_serve_socket.py, SCOPE002@tickets.md
