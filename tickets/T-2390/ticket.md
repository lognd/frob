---
id: T-2390
title: 'config-file keys are never validated: an unknown or misspelled frob.toml key
  is silently ignored'
state: in-progress
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a frob.toml containing a key no declared config schema claims, when
    any frob command loads config, then the unknown key is reported with its file
    and key name, rather than silently ignored.
  evidence: []
- text: Given a project that declares no config surface at all, when the check runs,
    then it reports that no configuration surface is declared and does not report
    a silent zero.
  evidence: []
- text: Given this repo's own frob.toml with all 148 leaf values, when the check runs,
    then it reports zero unknown keys, proving the check was not calibrated by weakening
    it.
  evidence: []
threat: null
component: config
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-18. frob validates its two input channels to wildly
different standards, and the file channel is the unvalidated one.

    CLI input          unknown flag -> argparse rejects it, and T-0578's
                       suggester even proposes the intended flag
    config-file input  unknown key   -> silently ignored

Evidence:
  - `AppConfig.model_config` is `{}`, so pydantic's default
    `extra="ignore"` applies across all 356 declared fields.
    `AppConfig(subcommand=None, path=".", tiemout_s=999, notakey="xyz")`
    constructs cleanly and drops both bogus keys with no diagnostic.
  - `frob.toml` in this repo carries 148 leaf values across 12 top-level
    tables (arch, check_base, docblocks, dup, gates, graph,
    min_frob_version, native, profile, refs, test, testing).
  - There is NO unknown-key validation anywhere in src/frob. Every
    "unrecognized" hit in the tree concerns CLI arguments, not config
    keys. `_build_external_config_kwargs` iterates the KNOWN field
    tuples (_STRING_FIELDS/_PATH_FIELDS/_INT_FIELDS/_FLOAT_FIELDS/
    _LIST_FIELDS/_BOOL_FLAGS) pulling from the parsed dict, so a key the
    file contains but no tuple names is never read and never reported.

WHY THIS MATTERS MORE THAN A TYPO. A misspelled `max_function_lines` in
[arch] does not fail -- the limit silently reverts to its built-in
default and the gate keeps reporting green while enforcing a threshold
the operator never chose. The config layer's version of
[[catalogued-is-not-enforced]]: the knob is present, documented, and
inert. Every gate whose strictness is configurable is exposed to this,
which makes it a silent correctness hole across the whole enforcement
surface, not a usability wart.

SAME FAMILY AS T-2387 (filed independently today): three T-2320 flags
parse but never reach AppConfig because `_BOOL_FLAGS` was not updated.
Both are "a configured value silently fails to reach its destination".
T-2387 is the CLI half and already has a purpose-built detector
(`find_dropped_cli_flags`, T-2004) whose test is currently RED on main.
This ticket is the FILE half, which has no detector at all.

REQUIRED SHAPE OF THE FIX (portability is a hard requirement -- see
T-2384; a check that only works on frob's own layout is the bug this
repo is currently paying down):
  - Report an unknown key in a config file against the DECLARED schema
    for that file, resolved through a declaration, not through a
    hardcoded reference to AppConfig. Reuse the existing
    `module:symbol` idiom already proven by
    `[[docblocks.commands]] parser = "frob.__main__:_build_parser"`.
  - A project that declares NO config surface must fail LOUDLY
    ("no configuration surface declared"), never report a silent zero.
    Silent-zero-on-unconfigured is precisely the defect class T-2384
    exists to remove; do not reintroduce it here.
  - Setting `extra="forbid"` on AppConfig is NOT sufficient on its own
    and may not even be safe -- verify before doing it. The forwarding
    layer builds kwargs from known tuples, so file keys never become
    model kwargs in the first place; a stricter model would catch
    programmer error at construction sites but not the operator typo in
    frob.toml, which is the actual bug. Fix the file path, and treat
    model strictness as a separate judgement with its own evidence.

Positive control is mandatory: a must-now-fire fixture (a frob.toml
carrying a plausibly-misspelled real key, e.g. `max_fuction_lines`,
which must be reported) AND a must-still-pass control (this repo's real
frob.toml, all 148 leaf values, must report zero once any genuinely
undeclared-but-intentional keys are declared). If the control does not
pass, the finding is that frob.toml has real undeclared keys -- report
them, do not weaken the check to accommodate them.
