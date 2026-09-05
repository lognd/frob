## Done report

VERSION001 read the `frob[native]` extra's pins BY NAME. T-3845 added a
second pin site (`frob-core`/`strata-core` in `[project].dependencies`)
that the by-name gate did not see, so the pending version bump could have
shipped frob 0.531.0 hard-depending on frob-core==0.530.0 -- a package
that cannot resolve -- with every gate green.

Fixed by matching by PACKAGE NAME across the whole document instead of by
table name: `_pin_sites` enumerates every list of dependency-specifier
strings reachable from `[project].dependencies`, every
`[project.optional-dependencies]` extra, and any `[dependency-groups]`
group; `_pin_in_specs` finds `frob-core`/`strata-core` in any of them. A
newly added pin site is now covered automatically, not by remembering to
add another hardcoded name -- the exact mistake this ticket closes one
level up.

MUST-FIRE fixtures added and passing: a skewed pin in
`[project].dependencies`, a loose (`>=`) pin in `[project].dependencies`,
and a skewed pin inside a newly-named extra (not `native`). The existing
five fixtures (matched/clean, skewed crate version, loose extra pin,
missing extra, mismatched extra pin) still pass unchanged. Verified
against the real repo's current pyproject.toml: 0 violations (both pin
sites agree at 0.530.0 today).

CHECKED EARLY per the brief: F-080's "config-only ticket can never land"
claim did not apply here -- T-3903 is scoped to a gate module plus its
test file, not a bare config edit, and T-3844/T-3845 (config-only) landed
same-day as counter-evidence anyway. F-080 itself is not a findable
ticket or file in this repo; treated as an unresolvable external claim
and did not block this ticket.

BUMP-PATH AUDIT (the ticket's second ask): confirmed the gap is real, not
theoretical. `frob release publish` calls `bump_patch_version`
(src/frob/release/__init__.py:410), which calls `rewrite_pyproject_
version` (src/frob/release/__init__.py:344) -- that function ONLY rewrites
`pyproject.toml`'s `version = "..."` line via a regex substitution.
Nothing in that path touches the frob-core/strata-core pins (either site)
or bumps frob-core/pyproject.toml or strata-core/pyproject.toml's own
version fields. Per-land bumping was deliberately deferred out of
`frob ticket land` by T-2462 (`_apply_release_bump_for_land` in
src/frob/app/ticket_runner/_land_cmd.py writes a changelog fragment only,
never touches pyproject.toml), so `bump_patch_version` really is the live
release-cut path, and it really does leave VERSION001 red after every
release bump. docs/guides/release.md#version-coupling-t-3011 already
discloses this residual gap in prose ("today's release cut requires a
human ... to bump all three version fields together by hand"). Filed as
T-3916 (bug, high priority) rather than fixed here -- extending
the bump path is materially more work than the pin-matching fix and
pyproject.toml/release/__init__.py carry other tickets' scope.

GENERALIZATION QUESTION (the ticket's third ask), answered rather than
left implicit: NOT generalizing VERSION001 into a repo-agnostic REL-family
rule now. typani T-026's proposal (detect any `<pkg>==<version>` pin
naming a sibling distribution structurally, not by two hardcoded names)
is the correct further step, but it is materially more design work
(structural sibling-package detection via workspace members / path
dependencies) than widening pin-site enumeration, which is what this
ticket needed to unblock the pending bump. Filed as T-3915
(feature, low priority) so the question is answered, not silently
dropped.

FOLDED IN (cheap): Series FE's tree-sitter-language-pack finding
(pyproject.toml:30, `>=0.13` with upstream now at 1.16.1, a major crossed
with no upper bound) is a different defect class from VERSION001 (a
loose third-party bound, not a sibling-crate lockstep pin) so it was not
folded into the gate fix itself; filed as T-3917 (bug, medium
priority). Checked first whether an existing ticket already covered it --
T-1598 exists but is about language-expansion research, not this version
bound, so a new ticket was warranted.

SCOPE-CLOSURE FINDING (encountered, not filed as a ticket -- resolved
in-line instead): `version_coupling_gate`'s pre-existing `frob:doc`
anchor pointed into docs/guides/release.md, a large shared doc file whose
OTHER anchors describe scripts/artifact_smoke.py, scripts/verify_
release_ci_status.py, and src/frob/doctor.py. Adding it to scope (to
satisfy SCOPE002/AFFECT001, both promoted WARN->ERROR by T-3844's
ratchet) pulled all of those in transitively (measured: error count went
5 -> 12, and further, once test/install-doc closure for doctor.py was
included). Rather than accept that disproportionate scope, dropped the
`frob:doc` edge and waived the resulting COV001 note, matching the exact
precedent src/frob/gates/_rule_id_scan.py's own SCANNED_BASES/RETIRED_
RULE_IDS waivers already document for this same tension (T-1010/T-1937).
Also worth naming: `frob check`'s SCOPE002 violation carries
`file="tickets.md"`, a virtual path with no real file to place a
same-file `frob:waive` on, so SCOPE002 itself is effectively unwaivable
by source directive in the common case -- exactly the gap T-3902's own
DOC006 finding (`--scope002-ack` referenced but not a real CLI option)
already points at. Not filing a duplicate ticket for it since T-3902
already names the same gap.

### Changed
```
 pyproject.toml                            |  13 +-
 src/frob/gates/_version_coupling.py       | 196 ++++++++++++++++++++++--------
 tests/unit/gates/test_version_coupling.py |  67 +++++++++-
 tickets/T-3903/ticket.md                  | 136 ++++++++++++++++++++-
 tickets/T-3915/ticket.md        |  38 ++++++
 tickets/T-3917/ticket.md        |  36 ++++++
 tickets/T-3916/ticket.md        |  37 ++++++
 7 files changed, 459 insertions(+), 64 deletions(-)
```

### Evidence
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_matched_versions_clean` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_skewed_core_version_fires` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_loose_pin_fires` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_missing_extra_fires` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_mismatched_extra_pin_fires` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_skewed_default_dependency_pin_fires` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_loose_default_dependency_pin_fires` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_pin_in_new_extra_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 3 error(s), 4368 warning(s), 927 waived
- error-findings: DEPR003@src/frob/app/fmt_runner.py, DOC006@tickets/T-3902/ticket.md, DRIFT001@src/frob/verify/_worker.py
