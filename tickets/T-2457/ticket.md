---
id: T-2457
title: fs.write capability detector matches bare open() regardless of mode, forcing
  seven false declarations
state: queued
kind: security
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a module whose only filesystem access is open(path, 'rb'), when the
    capability detector runs, then it reports no fs.write capability for that module.
  evidence: []
- text: Given a module calling open(path, 'w'), open(path, 'a'), or .write(...), when
    the detector runs, then fs.write is still reported, proving the false positive
    was not fixed into a false negative.
  evidence: []
- text: Given the seven declarations added solely to silence this detector, when the
    fix lands, then they are removed from design/frob.strata and the capability model
    no longer asserts write access those modules do not have.
  evidence: []
threat: tampering
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
The dangerous-ops capability detector cannot distinguish a READ-mode
`open()` from a write, so it reports `fs.write` for modules that only
read. The result is false capability declarations sitting permanently in
the security model.

MEASURED, and confirmed by an agent reading every implicated module: all
seven T-2390 config-schema modules contain ONLY `toml_path.open("rb")`.
There is no `.write(` call in any of them. Yet all of them trip:

    SELFAUDIT001: self-audit family SYS100 node=gates: capability
      'fs.write' observed at src/frob/gates/_dup_graph_schema.py:99
      but not declared

MECHANISM: the dangerous-ops table pairs the needles `("open(",
".write(")` for `fs.write` and matches on ANY needle being present. A
bare `open("rb")` therefore satisfies the fs-write rule on its own. The
mode argument is never consulted.

CURRENT STATE, and why this is worse than a noisy warning. Four modules
(`_arch_schema.py`, `_docblocks_schema.py`, `_native_schema.py`,
`_toplevel_scalar_schema.py`) already carry `fs.write` declarations in
`design/frob.strata` added purely to silence this, and three more are
being added for the same reason. That is SEVEN declarations asserting
the `gates` component can write to the filesystem via modules that
provably cannot. A capability model exists so that security and
architecture reasoning can rely on it; declarations that are known-false
degrade exactly the property the model is for, and they are
indistinguishable from genuine ones once written.

It also accounts for 56 of the 119 errors currently on main -- the
single largest cluster in the error floor -- so it is simultaneously the
biggest source of gate noise here.

FIX SHAPE:
  - Distinguish read-mode from write-mode opens. `open(path, "rb")` /
    `"r"` is not a write; `"w"`, `"a"`, `"x"`, `"+"` are. This is a
    token/AST-level question about the call's arguments, NOT a substring
    question -- do not "fix" it by adding more needles. The standing
    rule in this repo is that checks must parse and compare symbols,
    never substrings, and this finding is a direct consequence of
    breaking it.
  - Then REMOVE the seven false declarations from `design/frob.strata`.
    They exist only to silence this detector and must not outlive it.
    Each one added before this ticket lands should carry a comment
    saying so, which makes them findable.
  - Audit the rest of the dangerous-ops table for the same "any needle
    present" imprecision. `open(` is unlikely to be the only needle that
    over-matches, and the same pattern applied to network or exec
    capabilities would be more serious than a false fs.write.

POSITIVE CONTROLS:
  - must-now-be-silent: a module whose only filesystem access is
    `open(p, "rb")` reports no `fs.write` capability.
  - must-still-fire: a module calling `open(p, "w")`, `open(p, "a")`,
    or `.write(...)` is still reported -- do not fix the false positive
    by weakening detection into a false negative.
  - must-still-fire-indirect: whatever the current detector catches
    beyond literal `open`/`.write` (Path.write_text, shutil, os.replace,
    etc.) must keep being caught; enumerate what it detects today and
    verify the same set after.
