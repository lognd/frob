+++
id = "01M2PAKKJ730JH8KK6YGGSB61G"
title = "csharp event_declaration has no RawSymbol (_walk_csharp.py)"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-17T00:00:00Z"
updated = "2026-09-17T00:00:00Z"
aliases = ["T-4679"]
labels = ["milestone:0.540.0", "v1-cluster:D2"]
scope = ["src/frob/lang/_walk_csharp.py"]
+++

found while working T-4519: _cs_dispatch has no case for event_declaration, so a C# event member (e.g. 'public event EventHandler Changed;') never becomes a RawSymbol at all -- frob.xref/frob.docs cannot resolve it regardless of any change in those modules, since there is no symbol to find. Add an event_declaration case to _walk_csharp.py (likely SymbolKind.CONST, mirroring the property-declaration decision documented in that module's docstring) and a matching RawSymbol test. T-4519 pinned the current (missing) behavior in tests/unit/test_xref.py::test_csharp_event_declaration_is_not_yet_a_symbol using tests/fixtures/lang/csharp/nested_property_event.cs -- update/remove that pin once this lands.
