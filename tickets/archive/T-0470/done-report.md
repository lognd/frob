## Done report

Prong (1) LANDED as WAIVE003: a single frob:waive whose file/package-prefix match reaches violations across MULTIPLE packages is flagged as over-broad (src/frob/gates/__init__.py::_waive003_violations, registered in _KNOWN_GATE_RULES, run over the full assembled violation set). Non-vacuous tests: multi-package waiver flagged, single-package waiver not. Prong (2) PLACE001 class-ignore placement was prototyped and DELIBERATELY DROPPED as unsound (distance-from-class-start fires on the legitimate per-field waiver idiom in large pydantic classes; counterexample preserved in the dropped-PLACE001 comment near gates/__init__.py:961); refiled with that counterexample as T-0504. Implemented by the gates-chain agent (branch worktree-agent-ae00df0ca54dd3df2); its worktree ledger close was lost to the off-default-branch ledger-corruption hazard tracked as T-0505, so this Done report reconstructs the bookkeeping on main against the already-landed code.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
