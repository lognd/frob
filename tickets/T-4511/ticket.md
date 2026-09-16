---
id: T-4511
title: .NET BCL standard-library capability map
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-4505
parent: T-4513
tier: story
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_dotnet_bcl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: a registry data file mapping .NET Base Class Library APIs to frob capabilities, consumed by the C# resolver from T-4505 (blocked_by it -- the resolver must exist before this map has anywhere to plug in). Modeled on the existing per-language _dangerous_ops_*.py registry files.

Families to cover (each gets its own test):
System.IO -> fs.read/fs.write; System.Net/HttpClient/Sockets -> net/fetch_url; System.Diagnostics.Process -> exec; System.Reflection/Assembly.Load/dynamic -> eval/ffi; DllImport -> ffi; System.Environment -> env; Microsoft.Win32.Registry -> fs.write.

GIVEN a .cs call to File.Open or StreamWriter, WHEN scanned, THEN it maps to fs.read or fs.write per the registry, not a generic uncategorized finding.
GIVEN a .cs call to HttpClient.GetAsync or a raw Socket, WHEN scanned, THEN it maps to net/fetch_url.
GIVEN a [DllImport] attribute on an extern method, WHEN scanned, THEN it maps to ffi.
GIVEN Assembly.Load or a call through System.Reflection, WHEN scanned, THEN it maps to eval/ffi, distinct from a plain method call finding.