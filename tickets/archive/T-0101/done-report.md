## Done report

Decision (mine, documented in docs/modules/gates.md#waive-boundary):
loud WARN, not honoring. `frob-arch` diagnostics (long-function,
god-class, etc.) never become `Violation`s -- `frob.check` calls
`frob.arch.analyze_project` directly, bypassing `frob.gates` entirely --
so honoring waivers there means growing the waiver-matching machinery
into check's Diagnostic pipeline, a bigger surface change than this
ticket warrants. `perf`/`clones` (DUP*) are NOT unwaivable: `perf_gate`
and `dup_gate` already run inside `run_gates` and were already waivable
before this ticket; only `frob-arch` (and any typo'd/unregistered rule
id) was silently inert.

Changed: new `_KNOWN_GATE_RULES` (every static gate rule id) +
`_unwaivable_channel_rules` (ArchCategory's Literal args, introspected
via typing.get_args so it can't drift from frob.arch._models) +
`_waive002_violations` (src/frob/gates/__init__.py), wired into
`run_gates` alongside WAIVE001. A `frob:waive` naming an arch category
or any other unrecognized rule id now surfaces WAIVE002 (WARN,
always-on, itself waivable) explaining exactly why it is ineffective.
docs/modules/gates.md gained a rule-catalog row set + a "Waive boundary"
section recording the decision and the escape hatch if this changes.
Evidence: see evidence: list above (pytest --collect-only verified).
Filed: none (docs/** and tests/** were both in scope for this ticket).
Gates: `frob check --ticket T-0101 --base 80b5ced` and plain
`frob check` both exit 0 (see T-0108 (refiled here after its original draft id was lost at land) for why --base had to be pinned).
