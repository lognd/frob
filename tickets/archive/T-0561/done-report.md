## Done report

Implemented the T-0561 narrow carve-out: `frob.tickets._scope_add_conflicts`
now accepts an optional `root: Path | None = None` kwarg (threaded through
`_validate_scope_mutation` and `mutate_scope`, which already has `root`).
When an `--add` glob is a concrete literal path (no `*`/`?`/`[...]`), is a
TEST file by `frob.excludes.is_test_file`'s naming convention, and does
not yet exist on disk under `root`, a collision against another
IN_PROGRESS ticket's broader lease is downgraded from a hard reject to a
pass -- UNLESS the holder's own colliding scope entry is that exact same
literal path (a genuine same-file race, still refused).

Deliberately narrower than "any brand-new file anywhere": a bare
does-not-exist-on-disk check alone cannot tell a genuine additive test
file apart from a real expansion attempt into a busy module that merely
hasn't been created yet -- `test_add_leased_path_rejected_names_holder`
(pre-existing, still green) proves `src/frob/gates/foo.py` against an
in-progress `src/frob/gates/**` lease must still be refused, and that
non-existent path would have been wrongly exempted by an existence-only
check (test fixtures run against an empty `tmp_path`, where EVERY path
"does not exist yet"). Restricting to `is_test_file` paths matches the
ticket's actual repro (T-0546's blocked `tests/unit/
test_app_runners_batch6.py --add` against T-0160's `tests/**` epic) and
keeps the carve-out from silently widening into production source.

New tests: `TestNewFileCarveOut` (4 cases) covering the exempt path, the
still-existing-file non-exemption, the still-non-test-file
non-exemption, and the still-exact-same-holder-path non-exemption. All
pre-existing `TestMutateScope` tests (including
`test_add_leased_path_rejected_names_holder`, whose shape this ticket's
fix could have silently broken) stay green unmodified.

Also re-tagged 18 symbols across src/frob/graph/{__init__,_models}.py,
src/frob/gates/_parse_failures.py, tests/test_graph.py, and
tests/test_gates.py with `frob:ticket T-0561` alongside their existing
T-0544/T-0558 tags -- both of those tickets are now DONE, so their own
tags no longer satisfy COV002 for hunks still sitting in this same
uncommitted-to-main working diff (same precedent as T-0543's Done
report). No functional change to any of those symbols.

No public API change (`mutate_scope`'s external signature is unchanged;
`_scope_add_conflicts`/`_validate_scope_mutation`/
`_is_new_concrete_file_glob` are all private) -- no version bump.

### Changed
```
 .frob-release.json                |   4 +-
 CHANGELOG.md                      |  14 ++++
 pyproject.toml                    |   2 +-
 src/frob/gates/__init__.py        |   6 ++
 src/frob/gates/_parse_failures.py |  57 ++++++++++++++
 src/frob/graph/__init__.py        | 130 ++++++++++++++++++++++++++------
 src/frob/graph/_models.py         |  22 ++++++
 tests/test_gates.py               |  37 +++++++++
 tests/test_graph.py               |  96 +++++++++++++++++++++++-
 tickets.md                        | 154 ++++++++++++++++++++++++++++++++++++--
 uv.lock                           |   2 +-
 11 files changed, 493 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_under_broad_lease_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_existing_file_under_broad_lease_still_conflicts` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_non_test_file_under_broad_lease_still_conflicts` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_exact_match_of_holder_scope_still_conflicts` (pytest node id, verified passing when recorded)
