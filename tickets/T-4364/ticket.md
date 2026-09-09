---
id: T-4364
title: Audit final PERF/SEC/PII/ARCH/DOC/VET/WAIVE/etc T-3844-promoted rules for waivability/structural
  silence
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4346 (audit remaining T-3844-promoted rules for
waivability/structural silence).

T-4346's time budget covered the highest-suspicion cross-section of the
~270-rule remainder: every "git show <ref>:<path>" Violation-construction
site in the ENTIRE src/frob tree (not just gates/ and strata/, extending
T-4340's own scoped sweep) -- no second TICK005/COV002-shaped stale-git-
object read was found; DEBT001-003 (real frob:debt directive sites,
anchorable file:line, waivable by rebind/resolve); DEPLOY001-003 (fires
on zero findings in THIS repo because no deploy/ directory is committed
here at all -- confirmed this is the documented, deliberate opt-in
posture the module docstring states explicitly and attributes to the
SAME precedent sys_gate/decisions_gate already use for a model-absent
repo, not migration debris -- left at error); FFI001/002 (both
frob:describes-pragma target files, frob-core/frob_core.pyi and
strata-core/strata_core.pyi, exist and are current); KRB001-004 and the
REL200-397/SYS001-205 strata resource-contention family (confirmed these
are live deny-by-default proof engines run against this repo's own
.strata design models every check, not disabled/feature-gated shims --
zero findings because the current models satisfy the proofs, not because
the rule cannot fire).

NOT walked with the same per-rule rigor (time-boxed out of T-4346):
PERF005-014, SEC* (beyond SEC110 already promoted pre-T-3844), PII*
(beyond PII010/012), ARCH* (beyond ARCH001/101/102/103), DOC*, REG001-007
+ REG012, COMPLIANCE001-007, PROFILE001, WAIVE001-011 (non-cluster),
VET*, DEC000-003, DEBT-adjacent CROSSTICKET001/CVEFP001, DUP001-003,
WIRE001-003, FUZZ001-003, THREAT001-006, TODO001-003, CACHE001, CAP001,
CHECK001, CLAUDE001, BUDGET001, AUTOFIX001, AFFECT001-002, ARCHSCHEMA001,
CPPTHROW001, and the rest of the frob.toml [gates.severity] T-3844 block
not already covered by T-4328/T-4331/T-4340/T-4346.

Method (unchanged from T-4331/T-4340): for each rule, find every
rule=<ID> Violation-construction site; check whether the emitted
Violation carries a real anchorable file:line/symref (property 2 --
watch for hardcoded line=0 against a path a migration removed, though
note line=0 alone is not diagnostic -- many legitimate whole-file
findings anchor to line=0 against a file that DOES exist, so each hit
needs its target path existence checked, not just grepped); check the
containing function/module for a stale git-object read, a removed file
path, or a config/feature-flag gate that would make it silently
unreachable in this repo's current state (property 3, the
TICK005/COV002-T-1582 shape) as distinct from a documented, intentional
opt-in posture (the DEPLOY001-003 shape found by T-4346, which is NOT a
bug). Do NOT mass-demote -- report per-rule reasoning for anything left
at error, and for anything demoted or newly reachable, ask whether the
current tree actually violates it now that it can fire.
