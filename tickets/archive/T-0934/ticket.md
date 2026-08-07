---
id: T-0934
title: 'frob check: derived.lock self-deadlock under concurrent multi-worktree load'
state: dropped
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Observed while working T-0826: 'frob check --ticket T-0826' / '--only scope' hung indefinitely (traced past 590s) on a 12-core box under load from 10+ other agent worktrees each running frob check concurrently. lslocks showed the hung pid holding both a READ and a pending WRITE* lock on its OWN worktree's .frob/derived.lock with no other pid contending for that same file -- looks like an intra-process lock-upgrade self-deadlock (one thread holds LOCK_SH via one fd while another thread requests LOCK_EX via a second fd on the same inode) rather than genuine cross-worktree contention. Repro: run frob check --only scope in a fresh worktree while many sibling worktrees are also running frob check; capture /proc/<pid>/task/*/wchan for confirmation (locks_lock_inode_wait + futex_wait_queue observed). Reduced-load runs of the same command (frob ticket evidence, pytest) completed fine, so this is check-path-specific, likely in the derived-cache build/lock acquisition.

## Drop reason
- 2026-07-27: same T-0918 lock-reentrancy self-deadlock (READ held + WRITE blocked in one pid on derived.lock), independently reproduced by a second agent; T-0933 has the fix in flight (absorbed by T-0933)