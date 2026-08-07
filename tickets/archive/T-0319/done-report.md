## Done report

New `frob doctor` subcommand: src/frob/doctor.py (run_diagnosis,
DoctorReport, NativeExtensionStatus, NATIVE_EXTENSIONS, REMEDIATION_HINT) +
src/frob/app/doctor_runner.py, wired through __main__.py (_add_doctor_parser
in _add_workflow_subparsers), config.py (Subcommand.doctor, AppConfig.
doctor_json, from_external), and app.py (doctor_runner in the runner maps).
It imports frob_core AND strata_core, reports availability+version for each,
and exits nonzero with REMEDIATION_HINT (make core / make install-tool) when
either is missing; `frob doctor --json` emits the same DoctorReport
machine-readably. Verified live: `frob doctor` reports both natives available.
docs/guides/install.md's old "no dedicated frob doctor subcommand yet"
paragraph replaced with a real section.

Evidence (3 of 10 tests; all 10 pass): natives-absent (monkeypatched import
raise -> healthy False + hint), natives-present, and the CLI fail-loud
subprocess test (shadows strata_core via PYTHONPATH fixture, runs real
`python -m frob doctor`, asserts nonzero exit + "NOT importable" + hint).

Coordinator landing: reviewer APPROVED the code (10 real tests, genuine
non-dormant wiring, real fail-loud path) but REJECTED on REL001 (their
worktree was at a stale 0.12.0). On current main (0.33.0), `frob release
check` confirms 0.33.0's public-API delta since 0.32.0 already covers the
doctor surface; ran `frob release stamp` (904 public symbols incl. doctor at
0.33.0 -> .frob-release.json) and added the T-0319 CHANGELOG entry under
[0.33.0]. No version bump needed. Landed via 3-way + new-file copy.
