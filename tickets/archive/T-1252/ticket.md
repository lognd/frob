---
id: T-1252
title: 'strata: migrate design/frob.strata off deprecated fs/fs-read spellings'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- src/frob/strata/_threat.py
- tests/unit/strata/test_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_threat.py
  reason: THREAT002's DEFAULT_BENIGN_CAPABILITIES catalog only excuses the deprecated
    bare fs/fs-read kinds; migrating design/frob.strata to the T-0717 mode-qualified
    fs.write/fs.read spellings needs matching fs.write/fs.read BenignCapability entries
    added (kept alongside the old ones for backward compat with any consumer still
    declaring the deprecated spelling) or THREAT002 fails closed on every migrated
    node
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: evidence binding for the new fs.write/fs.read BenignCapability catalog entries
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
acceptance:
- text: design/frob.strata contains zero fs or fs-read plain declarations.
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- text: 'Every migrated blocks fs.write/fs.read declarations are semantically

    equivalent to the prior fs/fs-read pair for that block.'
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- text: frob check --only sys strata SYS gates is clean or no-worse than main.
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
threat: null
component: null
---
design/frob.strata declares the deprecated, un-mode-qualified filesystem
capability spellings (may fs, may fs-read) instead of the T-0717
mode-qualified spellings fs.write/fs.read (see src/frob/strata/_effects.py
_KIND_MAP: fs-write -> fs.write, fs-read -> fs.read; _capability_modes.py
marks fs-write/fs-read as deprecated aliases).

Migrate every declaration in design/frob.strata to the precise new
spellings:
- may fs-read -> may fs.read.
- may fs -> may fs.write (every block in this file used bare fs
  to mean the write-derived observation, per each blocks own header
  comment; where a block also reads, it already declares fs-read
  separately, migrated to fs.read alongside).
- Update stale comments that explain the old fs/fs-read scanner
  convention where they become wrong.

tests/unit/strata/*.py litmus-style tests that specifically exercise the
deprecated-alias normalization path are Python test fixtures, not .strata
files, and are testing the alias behavior itself -- left untouched.