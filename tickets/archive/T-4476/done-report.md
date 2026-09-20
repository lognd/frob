## Done report

Changed:
.github/workflows/release.yml::jobs.artifact-smoke (manylinux-aarch64 entry: os moved from ubuntu-latest to ubuntu-24.04-arm)
tests/unit/test_release_workflow_gate.py::TestArtifactSmokeAarch64UsesNativeArmRunner
docs/guides/release.md (native arm64 hosted-runner note)

Decision: PREFERRED FIX chosen, not the PLATFORM001 fallback. This repo
is public (gh repo view --json isPrivate -> false), and GitHub publishes
a hosted native arm64 Linux image, ubuntu-24.04-arm, free for public
repos since GA (Jan 2025). artifact-smoke's manylinux-aarch64 leg now
runs there instead of ubuntu-latest, keeping the smoke a genuine
install + frob execution on matching hardware rather than falling back
to a wheel-existence-only drop. build's manylinux-aarch64 entry is
UNCHANGED (still cross: true, built via QEMU on ubuntu-latest) -- only
the artifact-smoke leg moved, per ticket scope.

Evidence (frob:tests T-4476):
tests/unit/test_release_workflow_gate.py::TestArtifactSmokeAarch64UsesNativeArmRunner::test_manylinux_aarch64_smoke_runs_on_a_native_arm_image
tests/unit/test_release_workflow_gate.py::TestArtifactSmokeAarch64UsesNativeArmRunner::test_manylinux_aarch64_not_in_smoke_exempt_targets
Full file: pytest tests/unit/test_release_workflow_gate.py -q -p no:randomly -> 40 passed
YAML validated with python yaml.safe_load

Filed: none

Gates: frob check --ticket T-4476 clean against scope after sweep (2
pre-existing out-of-scope findings remain -- DRIFT001 on
src/frob/doctor.py and REF002 on docs/design/macos-portability.md --
neither touched by this ticket's diff). BUG002 waived via frob ticket
body --append-file: --check-repro reported TEST_ABSENT_AT_PARENT (test
written for this ticket) plus no local repro path for a CI-config
change; citing release run 34799974130.

Caveat stated per brief: the ubuntu-24.04-arm label's availability for
this repo was not independently confirmed via gh api (that endpoint
cannot list hosted runner labels); this is based on GitHub's documented
GA of hosted arm64 Linux runners for public repos (Jan 2025) and this
repo's public visibility. If the label turns out to be unavailable on
the next dispatch, the fallback is to drop the manylinux-aarch64
artifact-smoke leg with the same PLATFORM001 comment style macos-x86_64
uses (T-4470) -- not attempted here since the preferred fix was
requested first.

### Changed
```
 .github/workflows/release.yml            | 14 +++++++++-
 docs/guides/release.md                   | 20 ++++++++++++++
 tests/unit/test_release_workflow_gate.py | 46 ++++++++++++++++++++++++++++++++
 tickets/T-4476/ticket.md                 | 15 +++++++++++
 4 files changed, 94 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestArtifactSmokeAarch64UsesNativeArmRunner::test_manylinux_aarch64_smoke_runs_on_a_native_arm_image` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestArtifactSmokeAarch64UsesNativeArmRunner::test_manylinux_aarch64_not_in_smoke_exempt_targets` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 4848 warning(s), 967 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md
