## Done report

Verified rather than re-implemented: the coordinator sweep commits
a497008/428c753 ("fix(walk): route raw traversals through frob.excludes
helpers (WALK001)") landed on main earlier the same day this ticket was
filed and already migrated every os.walk/rglob site the ticket names
(gates/_secrets.py now uses git ls-files via frob.gitio.run_argv,
gates/_prework.py uses frob.excludes.load_exclude_globs +
_is_scan_path_pruned, gates/_baseline.py and gates/_coverage.py carry no
raw traversal at all, sys_gate/archgate_gate/tickets_gate consume a
pre-built GraphSnapshot rather than walking themselves, and
src/frob/tickets/__init__.py's own sweep already routes through the
shared prune helpers per its own docstring history). WALK001 no longer
fires unwaived anywhere in src/frob/gates/** or src/frob/tickets/** --
the remaining 14 WALK001 findings gate-wide are all outside this
ticket's scope and already carry honest frob:waive reasons from the
prior sweep (cache-dir scanners, bounded single-directory walks,
Cargo/npm workspace globs, doclink ** semantics).

Timed a fresh `uv run frob check --only gates`: archgate=2.89s,
secrets=1.88s, sys=0.71s, tickets=0.46s, prework folded into the
tickets/scope stages at 0.00s -- none anywhere near the ~350s baseline
this ticket describes; a second run with --ticket T-0335 confirms the
same (archgate=0.00s cache hit, secrets=1.98s, sys=0.76s, tickets=0.48s,
prework=0.00s).

No source changes were needed; this ticket's acceptance criteria were
already met by the prior sweep. The one gates-stage error
(docs/commands/sys.md:122 DOC003) is pre-existing and unrelated to
os.walk/prune work -- confirmed present before this ticket's start (no
local diff at ticket-start time).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
