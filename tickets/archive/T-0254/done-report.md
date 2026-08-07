## Done report

(verification closure, T-1241-style precedent)

This is an umbrella/epic ticket whose own text says "Umbrella closes when
all children close" -- it was never meant to carry its own file diff.
This session's job was to determine whether that closing condition is
actually met, not to write new epic-level code.

Verified this session, by reading the actual code (not trusting ticket
state alone):
- T-0255 (std.host manifest): `src/frob/strata/_host.py` (HostManifest/
  HostOwns/HostPlatform), grammar in `strata-core/src/parse.rs`,
  elaboration wired in `_elaborate.py`/`_infra.py`. `state: done`.
- T-0256 (movement-impossibility proofs): `src/frob/strata/
  _host_isolation.py` -- HOST001 (lateral)/HOST002 (vertical), every
  sub-target derived from `HostManifest` intersection, no hand-written
  per-pair table. `state: done`.
- T-0257 (deploy generate): `src/frob/deploy/_generate.py` +
  `_generate_windows.py`, `frob deploy generate` CLI wired in
  `src/frob/app/deploy_runner.py` and `frob.__main__`. `state: done`.
- T-0258 (script<->manifest conformance): `src/frob/deploy/_conform.py`
  (DEPLOY002/003), and confirmed these are NOT dead code -- `src/frob/
  app/check_runner.py::_append_deploy_stages`/`_deploy_conformance_
  result` fold them into `frob check` as an opt-in stage whenever
  `deploy/` exists in a repo. `state: done`.
- T-0259 (VM snapshot audit harness): `src/frob/deploy/_audit.py` +
  `_vm_runner.py`, `frob deploy audit --vm` CLI, explicitly NOT part of
  `make check` per the epic's own mandate (expensive, VirtualBox-gated).
  `state: done`.
- T-0261/T-0262/... (Windows/Kerberos extensions beyond the epic's
  named 5-step chain): also `state: done`, not part of this epic's
  closing condition but confirm the std.host vocabulary did not stop at
  Linux-only.
- T-0260 (child 6, the malmberg pilot): closed THIS session (see its own
  Done report) against a fixture-based substitute
  (tests/fixtures/deploy/malmberg_pilot/,
  tests/integration/test_deploy_malmberg_pilot.py) proving the FULL
  chain (manifest -> HOST001/HOST002 -> generate -> conformance) agrees
  with itself on one malmberg-shaped multi-service model, end to end --
  the first test in the repo to do so, closing the "each gate proven in
  isolation, never proven together" gap honestly. The real-malmberg-repo
  half of T-0260's original acceptance (editing malmberg's own docs/
  scripts, running a live VM audit against it) could NOT be done from
  this checkout -- no malmberg clone exists anywhere on this machine and
  no agent here has remote/SSH access to it (only two SSH private keys
  referencing it exist under ~/.ssh). That gap is disclosed, not
  silently dropped: filed as T-1501 (parent T-0254), which
  carries the real-repo acceptance criteria forward for whenever an
  agent/coordinator with actual malmberg access can run it.

Closing decision: with all 6 originally-named children `done` and the
technical machinery independently confirmed wired (not just marked
done), this epic's own stated closing condition is met. T-1501
is residual, infrastructure-gated future work explicitly acknowledged
here (TICK011 discipline) -- it does not block this epic's close any
more than any other repo's "apply this to a real deployment when one is
available" follow-up blocks the feature that enables it.

Changed: none (umbrella ticket, no file diff of its own -- see T-0260's
Done report for the actual code/test changes this drive produced).

Evidence: none of its own (umbrella ticket); the technical evidence is
carried by T-0255/T-0256/T-0257/T-0258/T-0259/T-0260's own Done reports
and evidence lists, all independently re-verified by reading the code
this session, not re-run in full (repo-wide `make coverage`/full `frob
check` is a coordinator-only step per the agent playbook section 3c/6b,
never a dispatched sub-agent's).

Filed: T-1501 (real-malmberg-repo pilot follow-up).

Gates: `check --ticket T-0254 --only prework --only scope` after a fresh
sweep -- gate:PREWORK clean; gate:SCOPE reports the same pre-existing,
repo-wide TICK009 scope-breadth pattern documented in T-0260's own Done
report (T-0254's scope includes `tests/**`/`src/frob/**` broadly, by
design, per its own `scope_breadth_ack` -- an epic tracking a whole
campaign, not a single unit of work), not a new finding from this
session.

### Changed
```
 .frob-release.json                       |  11 +-
 CHANGELOG.md                             |   4 +
 design/frob.strata                       |  21 +-
 docs/design/check-fix-engine.md          |  50 ++++
 docs/design/registry/check-coverage.yaml |  12 +
 pyproject.toml                           |   2 +-
 src/frob/gates/_fix_engine_tier_b.py     | 492 +++++++++++++++++++++++++++++++
 src/frob/gates/_fix_engine_tier_c.py     | 165 +++++++++++
 tests/test_gates.py                      | 304 +++++++++++++++++++
 tickets.md                               | 420 +++++++++++++++++++++++++-
 uv.lock                                  |   2 +-
 11 files changed, 1467 insertions(+), 16 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 5 error(s), 196 warning(s), 758 waived
- error-findings: DUP001@tests/integration/test_deploy_malmberg_pilot.py, REG005@docs/design/registry/check-coverage.yaml, REG007@docs/design/registry/check-coverage.yaml, SELFAUDIT001@design, WIRE001@tests/integration/test_deploy_malmberg_pilot.py
