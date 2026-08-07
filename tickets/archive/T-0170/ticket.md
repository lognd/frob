---
id: T-0170
title: kotlin capability-scanner column for android nodes
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_registry.py
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScan::test_kotlin_net_okhttp_detected
- tests/test_vet.py::TestCapabilityScan::test_kotlin_exec_runtime_exec_detected
- tests/test_vet.py::TestCapabilityScan::test_kotlin_client_storage_shared_preferences_detected
- tests/test_vet.py::TestCapabilityScan::test_kotlin_benign_file_has_no_capabilities
- tests/test_vet.py::TestCapabilityScan::test_language_for_known_and_unknown_extensions
- tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages
- tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_language_for_is_consistent_with_scanned_languages
designated_repro_test: null
threat: null
component: null
---
logand.app has an android node; no Kotlin pattern table exists, so its capabilities cannot be verified. Add kotlin as a language column per the T-0158 matrix discipline: pattern tables for the reserved kinds where Kotlin idioms exist (net: OkHttp/HttpURLConnection/Retrofit; exec: Runtime.exec/ProcessBuilder; client_storage: SharedPreferences/Room; fs; eval: unusual -- excuse honestly), per-cell fire fixtures, .kt/.kts extension mapping. Sequence after T-0158 lands the matrix.