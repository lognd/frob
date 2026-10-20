+++
id = "01M47RDFJX56SCTFTZJRQ1SC2B"
title = "Feed CrateDeps::implicit_usings_of into C# import resolution"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T04:44:11Z"
updated = "2026-10-06T04:44:11Z"
scope = ["crates/gob-symbols/src/csharp.rs"]
+++

found while working ~ECEBCQ1: dotnet.rs exposes project-wide implicit usings (ImplicitUsings plus Using items, per SDK) via CrateDeps::implicit_usings_of(path). csharp.rs/qualifier.rs import resolution (after ~JEN2C8Q) should consume it so calls on implicit-using namespaces are not left Unresolved.
