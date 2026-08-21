---
id: T-2805
title: 'native-staleness content-digest check is a permanent latch: a reproducible
  rebuild is byte-identical, so frob natives build can never clear NATIVE001'
state: in-progress
kind: bug
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_native_staleness.py
- src/frob/natives/_build.py
- tests/unit/strata/test_native_staleness.py
- tests/unit/test_natives_build.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/natives/_build.py
  reason: T-2805's fix needs a genuine-rebuild ATTESTATION distinguishable from a
    bare touch, which by construction cannot come from anything _native_staleness.py
    alone can observe (mtime/bytes are exactly what the touch attack fakes) -- only
    the actual build tool invocation (frob.natives._build.build_natives) can assert
    'a real compiler run just happened against this exact source'. Widening to that
    file (one small hook call after a successful crate build) plus both modules' existing
    test files, same shape as T-2793's scope correction.
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/strata/test_native_staleness.py
  reason: T-2805's fix needs a genuine-rebuild ATTESTATION distinguishable from a
    bare touch, which by construction cannot come from anything _native_staleness.py
    alone can observe (mtime/bytes are exactly what the touch attack fakes) -- only
    the actual build tool invocation (frob.natives._build.build_natives) can assert
    'a real compiler run just happened against this exact source'. Widening to that
    file (one small hook call after a successful crate build) plus both modules' existing
    test files, same shape as T-2793's scope correction.
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/unit/test_natives_build.py
  reason: T-2805's fix needs a genuine-rebuild ATTESTATION distinguishable from a
    bare touch, which by construction cannot come from anything _native_staleness.py
    alone can observe (mtime/bytes are exactly what the touch attack fakes) -- only
    the actual build tool invocation (frob.natives._build.build_natives) can assert
    'a real compiler run just happened against this exact source'. Widening to that
    file (one small hook call after a successful crate build) plus both modules' existing
    test files, same shape as T-2793's scope correction.
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured 2026-08-21 on the shared root

`stale_natives` reported both natives stale. I ran the documented
remediation:

    frob natives build
    -> "strata_core built cleanly"
    -> "frob_core built cleanly"   (rc=0)

`NATIVE001` STILL fired immediately afterwards. Inspecting the detector's
own output:

    strata_core: reason=content-digest source_dir=strata-core
       artifact: Fri Aug 21 03:44:29 2026     <- my rebuild, minutes old
       source:   Wed Aug 19 05:24:28 2026     <- two days older
    frob_core:   reason=content-digest  (same shape)

So the MTIME check says fresh -- the artifact is newer than its source. It
is T-0513's content-digest branch that latches.

## Mechanism (src/frob/strata/_native_staleness.py:305)

    if artifact_digest == prior["artifact"] and source_digest != prior["source"]:
        stale.append(... reason="content-digest")
        # do NOT overwrite the stamp here -- the next run must keep
        # detecting the same unrebuilt edit until a real rebuild
        # actually changes the artifact bytes.
        continue

The comment states the intent exactly, and the intent is sound for the case
T-0513 was written for (a bare `touch` advancing mtime with no rebuild).

The flaw is the exit condition. `maturin --release` on unchanged source is
REPRODUCIBLE, so a genuine rebuild produces byte-identical output. A real
rebuild and no rebuild at all are therefore indistinguishable to this test,
and the branch deliberately never refreshes the stamp. Once entered, the
only escape is an artifact byte change -- which a correct rebuild of
unchanged source will never produce.

It is a LATCH: `frob natives build`, the tool's own documented remediation,
cannot clear it.

## Why this was expensive

`NATIVE001` makes `frob check` FAST-EXIT before any gate runs -- measured at
14 seconds / 3152 bytes, versus 334s / 1.5MB for a real run. So while
latched, `frob check` is unusable in that checkout entirely.

Worse, that abort was being recorded as the rapid sweep's rolling baseline,
so verification reported GREEN having run zero gates (T-2793, now landed).
T-2793 fixes the false-green consequence. THIS ticket is the trigger: while
the latch persists, `frob check` simply cannot complete.

## Workaround used, which is NOT the fix

Deleting `.frob/native-content-stamps.json` (local, gitignored) forces a
re-baseline: the "first observation" path trusts mtime and records a fresh
stamp. Confirmed: stale count went to 0 and a full 334s check then ran.
Safe ONLY because mtime independently showed the artifact newer than source;
doing this blindly would hide genuine staleness.

## Required shape

The digest check needs an escape that a legitimate rebuild can trigger.
Options to weigh, not a prescription:
- Record a rebuild EVENT (e.g. `frob natives build` stamps a build marker
  the detector consults) so "rebuilt but byte-identical" is distinguishable
  from "never rebuilt".
- Compare the source digest against the digest at last BUILD rather than at
  last OBSERVATION, so an unchanged-source rebuild reconciles.
- Refresh the stamp when the artifact's mtime is newer than the recorded
  source observation AND the source digest is unchanged since the artifact
  was produced.

Whatever is chosen must preserve T-0513's actual purpose: a bare `touch` on
the artifact with a genuinely edited source must STILL be caught.

## Positive controls, both directions

- Latched state + a genuine `frob natives build` (byte-identical artifact)
  -> NATIVE001 CLEARS. This is the case that fails today.
- `touch` the artifact after a real source edit, no rebuild -> NATIVE001
  STILL FIRES. This is T-0513's original purpose and must not regress;
  without this control the fix is indistinguishable from deleting the
  digest check.
- Genuine source edit + genuine rebuild (artifact bytes DO change) ->
  clears, as today.
- Fresh checkout, no stamp file -> first-observation path behaves as today.

## Dead end, do not chase

`target/` build artifacts are NOT the cause. I initially theorised that
`_newest_mtime` was picking up `frob-core/target/release/build/.../out/private.rs`
and thus always seeing source newer than artifact. That is FALSE: `target`
is in `frob.excludes.BUILTIN_SKIP_DIRS` and `walk_pruned` prunes it. The
mtime comparison is correct; the digest branch is the problem.
