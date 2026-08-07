---
id: T-0259
title: 'frob deploy audit --vm: VirtualBox snapshot-diff harness proving artifact-free
  uninstall'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0256
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/deploy/**
- scripts/**
- Makefile
- docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/deploy/test_audit.py::TestProofs::test_af_fails
- tests/unit/deploy/test_audit.py::TestProofs::test_ie_extra
- tests/unit/deploy/test_vm_runner.py::TestAvail::test_run_vm_audit_skips_cleanly
designated_repro_test: null
threat: null
component: null
---
T-0254 child 5. The expensive empirical audit, NOT in make check: dedicated `make deploy-audit` / `frob deploy audit --vm <name>`. VBoxManage workflow -- a state CHECK (snapshot capture + status/health assertion) is interleaved at EVERY checkpoint per user 2026-07-19, the exact sequence being: restore base snapshot -> CHECK C0 (capture S0 baseline: filesystem manifest w/ hashes+ownership+modes via ssh, /etc/passwd+group, systemd unit files+enabled set, listening sockets; AND assert status.sh reports not-installed) -> install.sh -> CHECK C1 (capture S1; assert status.sh reports healthy -- catches a broken install immediately) -> install.sh AGAIN -> CHECK C1' (capture S1'; assert healthy) -> uninstall.sh -> CHECK C2 (capture S2; assert status.sh reports not-installed, cleanly gone). Running status.sh at every checkpoint means each state is verified to MATCH THE MODEL, not merely snapshotted. PROOFS: idempotence S1' == S1 EXACTLY; artifact-freeness diff(S0,S2) EMPTY; install-exactness diff(S0,S1) == HostManifest EXACTLY (nothing extra, nothing missing); plus the three status assertions (not-installed / healthy / healthy / not-installed at C0..C2) -- all modulo a documented allowlist (logs/journal, machine-id class) each entry justified in docs. Emits an attestation JSON (timestamps, snapshot ids, diff digests) recordable as ticket evidence via --evidence-cmd (T-0215) and referenced as L4-class evidence for the movement claims (T-0256/T-0082 evidence-ladder precedent). Graceful degrade when VBoxManage absent: clear SKIPPED, never fake pass. Unit-test the diff/compare logic with fixture state captures so the logic itself is covered in the normal suite without a VM.