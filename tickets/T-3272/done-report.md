## Done report

Decision (option 2, "may be cleaner", per the ticket's own framing): v2
becomes the mode a repo with NO ledger at all initializes into on first
`frob ticket new` -- the EXISTING T-1553 behavior (`_store_mode` already
defaults an empty repo to "v2"). This required zero new template work:
removed the `tickets.md.j2` seed and its manifest entry from all seven
scaffold manifests (python-tool, python-library, pyo3-library, cpp-library,
cpp-tool, pybind11-library, web-app -- the ticket said "six", there are
actually seven registered types, verified via list_project_types()).
No second, config-declared "v2 mode" flag was introduced; `_v2_glob`'s
structural detection stays the sole source of truth, as required.

Seed-content answer: none. An empty `tickets/` directory cannot be
committed to git, so the scaffold ships NO ledger content of any shape --
not even an empty directory. v2 initializes lazily, identically to how a
from-scratch repo with no scaffold at all already behaves. This mirrors
the existing precedent in the same manifests (`invariants/.gitkeep`) but
deliberately does NOT add a `tickets/.gitkeep`: an empty `tickets/`
directory with nothing under it would not itself change `_store_mode`
(`_v2_glob` looks for `tickets/T-*/ticket.md`, not the bare directory), so
a gitkeep there would be inert boilerplate, not a functional seed.

Checked first, per the ticket's instruction: the frob.toml template,
Makefile, and CI workflow templates for every type reference
`docs/modules/tickets.md` (the doc guide) in a comment, never the ledger
path `tickets.md` itself -- verified via git grep across
src/frob/scaffold/data. No template depends on the monofile existing.

v1 repos are unaffected: `_store_mode` still returns "single" whenever
`tickets.md` already exists on disk with no v2 tree, and
`migrate_v1_to_v2` is untouched and still works, both proven directly (not
via the scaffold) since a v1 repo need never have been scaffolded by frob
at all.

Investigating this surfaced a SECOND bug (confirmed by direct repro, not
assumed): `frob ticket migrate --to v2` silently no-ops on a v1 repo whose
`tickets.md` has zero tickets in it (exactly what the OLD scaffold
template produced) -- `migrate_v1_to_v2` returns `Ok(0)` for both "already
v2" and "v1 with nothing to migrate", so the CLI's "already v2-mode (or
nothing to migrate)" message is genuinely ambiguous, and more importantly
the repo is left in v1 forever: LEDGERV1001's own documented remedy does
not clear its own warning on this exact repo shape. Filed as T-3282
(out of this ticket's scope -- it affects existing v1 repos, not the
scaffold path this ticket owns).

Fixtures:
- MUST-FIRE: test_freshly_scaffolded_project_is_v2_must_fire (renders a
  real project, asserts _store_mode == "v2", then calls new_ticket and
  asserts tickets/<id>/ticket.md exists)
- MUST-STAY-QUIET: test_existing_v1_repo_unaffected_must_stay_quiet
- THIRD: test_migrator_still_works_on_v1_repo_third_fixture (creates a
  real v1 ticket via new_ticket, then migrate_v1_to_v2 moves it to v2 and
  leaves tickets.md in place, matching the migrator's documented
  non-destructive contract)
- All-type coverage: test_render_project_all_registered_types_succeed
  and test_render_project_all_types_default_to_rapid_profile, both
  iterate list_project_types() (all seven types)

Docs updated: docs/commands/scaffold.md (removed the stale `tickets/`
claim from the python-tool contents row, added a paragraph stating the
new default and pointing v1 repos at the existing migrator);
docs/design/ledger-v2.md section 7 step 4 (added a T-3272 sub-note tying
the scaffold fix to the T-1553 cutover it was defeating).

Filed: T-3282 (frob ticket migrate --to v2 no-ops on a zero-ticket v1
ledger; out of scope for this ticket).

Gates: frob check --ticket T-3272 --only scope --only prework clean.
frob ticket sweep T-3272 re-run after scope --add. Touched-set unit tests
green (17/17 in tests/unit/test_scaffold_project.py, plus the
all-registered-types system test). `frob test --base main` additionally
ran the repo's separate "strata" test language suite because this diff
touches two unmapped `.md` doc files, which the selector's fallback
resolves to a suite-wide run across every language, not just python --
that fallback-triggered strata run is unrelated to this diff's scope
(scaffold/tickets code only) and is not evidence of a regression here.

### Changed
```
 docs/commands/scaffold.md                          | 11 +++-
 docs/design/ledger-v2.md                           | 10 ++++
 src/frob/scaffold/data/shared/python/tickets.md.j2 |  4 --
 src/frob/scaffold/project.py                       |  7 ---
 tests/unit/test_scaffold_project.py                | 69 ++++++++++++++++++++++
 tickets/T-3272/ticket.md                           | 55 ++++++++++++++++-
 6 files changed, 143 insertions(+), 13 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
