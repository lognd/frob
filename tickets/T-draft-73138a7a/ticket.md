---
id: T-draft-73138a7a
title: 'T-5808 native reuse overwrites the running process own loaded extension in
  place with a STALE artifact: every land segfaults in strata_core parse_source'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob
branch: dev
scope:
- src/frob/natives/_build.py
- tests/unit/test_natives_build.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 2938
  new_length: 3150
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-26 after T-5808 landed (dev e98e686cbc): three consecutive
`frob ticket land --drain` runs died with rc=139 (T-5756 twice, T-6528,
T-5815), faulthandler showing the same frame every time:
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->    frob/strata/_parse.py:79 parse_module -> strata_core.parse_source
    <- _design_load.load_design_ids <- _fix_engine_sync._capability_counts_at_head
    <- fix_sys111_capability_ratchet_sync <- apply_tier_a_fixes
    <- _land_cmd._tier_a_pre_land_step <- _absorb_pre_land_fixes <- _land_core_prepare
The land log right before it: "stale_natives: 2 native(s) stale vs their
own source: [strata_core, frob_core]" -> "run_gates: T-1213 auto-rebuild
triggered ... succeeded" -> "stale_natives: 2 native(s) stale" again.

Cause, verified on disk: `_try_reuse_native` -> `_copy_native_package`
(src/frob/natives/_build.py) uses `shutil.copy2` to write the reused
artifact into THIS interpreter's own site-packages (`_native_package_dir`
= sysconfig purelib of the running land process). Two defects compound:
1. In-place overwrite of a loaded shared object. The root .venv's
   strata_core.abi3.so has inode unchanged, ctime 2026-09-26 11:51:48
   (the copy) and mtime 2026-09-25 06:38:04 (copy2 preserves the source
   mtime). The running land process had that .so mmapped; the next call
   into it segfaulted. `maturin develop`/pip replace files by unlink and
   rename (new inode), which is why the pre-T-5808 rebuild path never
   crashed the running process.
2. The reused artifact is STALE: mtime 2026-09-25 06:38 is older than the
   last crate-source change (2361c0beef, 2026-09-25 09:53), and
   stale_natives still reports stale right after the "successful"
   reuse, so the digest/stamp match admitted an artifact built from an
   older source tree.
Coordinator mitigation applied: deleted
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->.git/frob-cargo-target-cache/native-reuse-stamps.json (backup in the
session scratchpad) and rebuilt root natives with a real maturin build.

Deliver: (a) the reuse copy writes to a temp name in the destination
directory and `os.replace`s each file (new inode, atomic), never
truncating a file the current process may have loaded; (b) never copy
into the RUNNING interpreter's site-packages when that native module is
already imported in this process -- log and fall through to the rebuild
(which itself must not be applied in-process; the T-1213 auto-rebuild
must re-exec or defer, same class as T-5814's drain re-exec); (c) the
reuse stamp records the crate-source digest the artifact was built
from and reuse requires equality with the CURRENT digest plus a
post-copy stale_natives check that returns clean, else the copy is
rolled back and a real build runs; (d) positive control: a test that
imports a fake native, runs the reuse copy over it, and asserts the
loaded module's file inode is untouched and the new file has a new
inode; a second test plants a stamp whose digest predates a source
edit and asserts reuse is refused.
