## Done report

REL001's remedy reads "bump the version to >= X, then run: frob release
stamp". Stamping is the half that appears to work on its own -- and it
DOES silence the gate, because stamping rebaselines the recorded public
API at whatever version is current. So running just the stamp half turns
a real un-released API change into a green gate.

I did exactly this earlier today, at 0.293.0, and caught it only by
noticing afterwards. That is the definition of a footgun the tool can
detect and therefore should not permit.

`stamp` now runs the SAME computation REL001 uses -- `diff_class` against
the recorded manifest, then `required_version` -- and refuses with
`ReleaseError.UnbumpedApiChange` when the current version is short,
writing nothing. `--allow-unbumped` is the explicit override, in the same
loud justification-required shape the repo already uses for
`--skip-mutation-evidence` and `--allow-cross-ticket`.

Two cases deliberately do NOT refuse: a first-ever stamp (no manifest to
be short of) and an adequately bumped version (the correct order still
works untouched).

The guard proved itself immediately: its own change altered `stamp`'s
signature, and the first stamp attempt after implementing it was refused
until 0.295.0 was set. A test asserts the refusal writes NOTHING, since a
partial write would rebaseline the very API it just rejected.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_refuses_when_api_changed_and_version_not_bumped` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_allow_unbumped_is_an_explicit_override` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_allows_when_version_is_bumped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 9 error(s), 1654 warning(s), 698 waived
- error-findings: AFFECT001@src/frob/app/release_runner.py, AFFECT001@src/frob/release/__init__.py, COV001@src/frob/release/__init__.py, COV005@src/frob/release/__init__.py, E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215, PRE001@tickets/T-1381, SELFAUDIT001@design
