+++
id = "01M44YQSZ3YEXRDW9RKER9HRA2"
title = "gob-symbols: C# units, attributes, partial types and preprocessor conditions"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-05T02:36:57Z"
updated = "2026-10-05T03:55:51Z"
idempotency_key = "d94-sym"
scope = ["crates/gob-symbols/src/csharp.rs", "crates/gob-symbols/src/registry.rs", "crates/gob-symbols/src/adapter.rs", "crates/gob-symbols/src/model.rs", "crates/gob-symbols/src/lib.rs", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/src/symref.rs", "crates/gob-symbols/Cargo.toml", "crates/gob-symbols/tests/csharp.rs", "Cargo.lock", "crates/gob-symbols/src/view.rs", "crates/gob-symbols/src/graph.rs", "crates/gob-symbols/tests/corpus.rs", "crates/gob-symbols/tests/corpus/csharp/**", "crates/gob-symbols/tests/snapshots/corpus__csharp_*.snap", "docs/reference/fidelity.md"]

[[links]]
kind = "blocked-by"
target = "01M44YQSHSC4N13E98FN2HND27"

[[acceptance]]
text = "Given a C# file with a file-scoped namespace, a partial class split over two files, a record, an interface, a property and a local function, when the symbol graph is built, then each is a unit and the partial class is one unit with two spans"
bound = true

[[acceptance]]
text = 'Given a method carrying [SerializeField], [Test] or [MenuItem("x")] attributes, when the graph is built, then the unit lists the attributes with names and argument text'
bound = false

[[acceptance]]
text = "Given code under #if UNITY_EDITOR and an #else branch, when the graph is built, then both branches yield units and each carries its condition"
bound = false

[[acceptance]]
text = "Given a C# construct the adapter does not model, when frob check runs, then it is reported Unresolved, not clean"
bound = false
+++

New first-party adapter crates/gob-symbols/src/csharp.rs registered in registry.rs and adapter.rs (model: rust.rs and python.rs, code-model.md section 3). Units: namespaces (file-scoped and block), types (class, struct, record, interface, enum, delegate), members (methods, constructors, properties, indexers, events, fields, operators, local functions). Partial types merge into one unit with several spans across files (model.rs). Attributes become attributes on the unit, with the attribute type name and the argument text kept for later vocabulary matching (Unity pack, test detection). Preprocessor: both #if branches are scanned and each unit carries its condition (for example UNITY_EDITOR), so editor-only code is neither dead in player builds nor the reverse; #if inside a member body is Unresolved for the enclosing member's digest stability, never silently dropped. Base types (`: MonoBehaviour`) are recorded as facts on the type unit. Constructs not modelled are Unresolved. Imports and calls are the next story.
