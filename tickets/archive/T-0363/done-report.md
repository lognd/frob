## Done report

Actual pre-fix unwaived PERF004 count was 4 (not 8). Dispositioned the 3
in-scope src/frob/** sites as reasoned frob:waive (each is a genuine
once-after-loop sort the token/bracket-depth heuristic false-positives on,
being indentation-blind): dup/_template.py:159, graph/__init__.py:153,
vet/_capability.py:344. The 4th site (tests/test_dup_prefilter.py:52) is
out of src/frob/** scope -- filed as T-0366. Re-audited existing perf
waivers (strata/_policy.py:94/106, tickets/_land.py:141,
vet/_containment.py:376) -- all still sort once outside/after their loops,
reasons hold, no drift since T-0161. Post-fix: `uv run frob check --only
perf` = 29 waived, 0 unwaived. The underlying detector blind spot is filed
as T-0367 (make PERF004 AST/indentation-aware so these waivers can be
removed). No thresholds loosened; all changes comment-only frob:waive.
Evidence: existing test_dup_template coverage over build_group_template
(one of the touched functions).
