---
id: T-2466
title: LEXCHECK001 scans only gates/ and only re.* calls, so it missed a substring-matching
  security detector in vet/
state: queued
kind: security
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_lexical_selfcheck.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a detector in src/frob/vet/ performing needle matching via bytes.find,
    when LEXCHECK001 runs, then it is reported -- using T-2457's own pre-fix code
    as the fixture.
  evidence: []
- text: Given the sites LEXCHECK001 legitimately exempts today, when its scope is
    widened, then those remain exempt, proving coverage was gained without loosening
    exemptions.
  evidence: []
- text: Given any LEXCHECK001 result, when it is emitted, then it names the scope
    actually scanned, so a count cannot be read as repo-wide when it is not.
  evidence: []
threat: tampering
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
The meta-checks that police detector QUALITY are themselves scoped to
one package, so detectors living anywhere else are unpoliced. This is
not hypothetical: it is exactly why T-2457 shipped and survived.

MEASURED:

    LEXCHECK001 (src/frob/gates/_lexical_selfcheck.py)
      scans: src/frob/gates/**/*.py    -- its own docstring, line 13
    PORT001     (src/frob/gates/_port_selfcheck.py)
      scans: src/frob/gates/** only    -- disclosed, widening filed as T-2405

WHAT THIS MISSED. T-2457 was a `fs.write` capability detector that
matched the bare needle `open(` without consulting the mode argument, so
every read-only `open(path, "rb")` was reported as a filesystem WRITE.
It forced TEN false capability declarations into `design/frob.strata`,
asserting that the `gates` component can write to the filesystem via
modules that provably cannot -- degrading the exact property a
capability model exists to provide. It was the largest single cluster in
the error floor.

LEXCHECK001 exists precisely to catch a detector doing lexical matching.
It missed this one for TWO independent reasons, both worth fixing:

  1. SCOPE. The detector lives in `src/frob/vet/_capability_core.py` and
     `_dangerous_ops_python.py`. LEXCHECK001 only scans
     `src/frob/gates/**`, so the file was never examined at all.
  2. TRIGGER. Even had it been scanned, LEXCHECK001's trigger requires
     `re.search`/`re.match`/similar, while the dangerous-ops matchers
     use plain `bytes.find`. Needle-matching and `Violation`
     construction are also split across separate modules, a gap the
     module's own docstring already discloses.

So a security-relevant detector performed substring matching, in
violation of this repo's standing "parse symbols, never substrings"
rule, in full view of a meta-check built to forbid that -- and the
meta-check could not see it on two axes at once.

THE GENERAL PROBLEM: a meta-check whose scope is narrower than the
class of code it polices creates a false sense of coverage. Its green
result is read as "no detector does lexical matching" when it means "no
detector IN src/frob/gates DOES LEXICAL MATCHING VIA re.*". That is the
[[silent-zero]] shape applied to meta-checks: a true statement about a
subset, read as a statement about the whole.

FIX SHAPE:
  - Widen LEXCHECK001 to every package that can contain a detector, not
    just `gates/`. `vet/` is proven necessary; `strata/`, `arch/`,
    `check/` are likely candidates -- enumerate rather than guess.
  - Widen the trigger beyond `re.*` to the byte/string search calls
    actually used (`bytes.find`, `str.find`, `in`, `startswith`,
    `endswith` on content), and handle the split-module shape where
    matching and Violation construction live in different files.
  - MOST IMPORTANT: whatever the final scope is, the check must REPORT
    IT alongside its result, so a count can never be read as repo-wide
    when it is not. PORT001 already does this after T-2388 -- it logs
    `scanned N tracked file(s) under src/frob/gates/** ONLY (not
    repo-wide)`. Copy that convention exactly; it is the cheapest part
    of this ticket and the part that prevents the next false-coverage
    reading.
  - Coordinate with T-2405, which widens PORT001's scope for the same
    reason. Consider whether both meta-checks should share one
    "packages that contain detectors" declaration rather than each
    hardcoding its own -- two hardcoded scopes will drift apart.

POSITIVE CONTROLS:
  - must-now-fire: a detector in `src/frob/vet/**` doing needle matching
    via `bytes.find` is reported. Use T-2457's own pre-fix code as the
    fixture -- it is a real, known-bad input, which beats a synthetic one.
  - must-still-pass: the legitimately-lexical sites LEXCHECK001 already
    exempts stay exempt. Its `_SELF_EXCLUDED_FILES` and allowlist exist
    for reasons; do not widen scope by loosening exemptions.
  - must-report-scope: the emitted count names the scanned scope.
