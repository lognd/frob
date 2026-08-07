## Done report

Changed:
- src/frob/arch/_models.py::ArchCategory (added illegal-states-representable,
  primitive-obsession, parse-dont-validate, boolean-flag-param; preserved
  T-0696 async-hazard values added same day)
- src/frob/arch/_typedesign.py::check_illegal_states_representable
- src/frob/arch/_typedesign.py::check_primitive_obsession
- src/frob/arch/_typedesign.py::check_parse_dont_validate
- src/frob/arch/_typedesign.py::check_boolean_flag_param
- src/frob/arch/_typedesign.py::run_typedesign_checks
- src/frob/arch/_typedesign.py: deleted local TypeDesignCategory/
  TypeDesignSeverity/TypeDesignSuggestion; module now imports and builds
  frob.arch._models.ArchSuggestion directly
- docs/modules/arch.md: type-driven-design-checks section rewritten to
  drop the stale scope-lease note and the now-nonexistent
  `TypeDesignSuggestion::describes` doc anchor

Evidence:
- tests/unit/test_arch.py::TestIllegalStatesRepresentable (2 cases)
- tests/unit/test_arch.py::TestPrimitiveObsession (2 cases)
- tests/unit/test_arch.py::TestParseDontValidate (2 cases)
- tests/unit/test_arch.py::TestBooleanFlagParam (2 cases)
- tests/unit/test_arch.py::TestRunTypeDesignChecks::test_combines_all_four_checks
- full tests/unit/test_arch.py (215 tests) green
- frob test --base main: [PASS] python exit=0 30.15s (touched-set selection)
Filed: none
Gates: frob check --ticket T-0892 clean (0 errors, 2325 warnings, 219 waived)
