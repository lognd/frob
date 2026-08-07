## Done report

Changed:
- src/frob/strata/_threat.py::BenignCapability
- src/frob/strata/_threat.py::ThreatViolation
- src/frob/strata/_threat.py::_entries_by_capability_kind
- src/frob/strata/_threat.py::_capability_violation
- src/frob/strata/_threat.py::check_capability_completeness
- src/frob/strata/_threat.py::_fired_obligations
- src/frob/strata/_threat.py::evaluate_threats
- src/frob/strata/__init__.py (export BenignCapability, check_capability_completeness)
- docs/strata/threat.md (phasing anchor + phase-B shipped note)

THREAT002 (precondition/capability completeness) added at the model
level per docs/strata/threat.md#phasing item B: every `may`-declared
capability kind is classified against the sink taxonomy or excused by a
`BenignCapability(kind, reason)` entry (reason non-empty, enforced via
`Field(min_length=1)`); unclassified is a deny-by-default THREAT002
violation. Single-source structural fix per review: removed the
module-level `_CAPABILITY_OBLIGATIONS`/`_SINK_TAXONOMY` globals (which
were pinned to the default `CWE_CATALOG` and would silently diverge from
`_fired_obligations` under a non-default `catalog` argument) and
replaced both with one function, `_entries_by_capability_kind(catalog)`,
that both `check_capability_completeness` and `_fired_obligations` call
over the SAME `catalog` argument they were given -- proven by
`test_non_default_catalog_moves_the_taxonomy_with_it` and
`test_thin_catalog_shrinks_the_taxonomy_with_it`. `evaluate_threats` now
conjoins THREAT001 + THREAT002 + THREAT003 and gained a `benign`
parameter. The code-level half (joining `_effects.py`'s extracted
net/fs/exec sinks against this taxonomy) stays phase C, documented in
the module docstring, since it needs the finer capability grammar
`_effects.py` itself defers.

Evidence: 11 new pytest node ids (listed above), bound via
`frob:tests src/frob/strata/_threat.py::<symbol> kind="unit"`
directives in tests/unit/strata/test_threat.py.

Filed: none (no out-of-scope discoveries).

Gates: `uv run frob check` exit 0, clean. `frob test --base main` not
run separately; verified instead via full-suite pytest (300 tests under
tests/unit/strata/, all green, including the 11 new THREAT002 tests)
and `frob check` clean. No waivers added by this ticket beyond the
pre-existing PERF003/PERF004 waivers already on neighboring lines this
ticket's edits shifted line numbers for.
