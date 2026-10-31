+++
id = "01M64VBRNZ32N2JR6EYVVKBEKG"
title = "CAP: C# P/Invoke (DllImport) and typed instance-method receivers; TS Express app.listen"
type = "story"
category = "done"
outcome = "done"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-10-29T22:09:21Z"
updated = "2026-10-31T00:48:27Z"
scope = ["crates/gob-symbols/**", "crates/grimble-bind/**", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = "C# DllImport and LibraryImport extern declarations are reported as ffi capability uses, with a regression test in crates/grimble-check/tests/symbolic_audit.rs"
bound = true

[[acceptance]]
text = "A C# typed parameter or field calling an instance method (for example HttpClient.GetAsync) resolves to the declared type and fires the matching capability, or is Unresolved, never silent"
bound = true

[[acceptance]]
text = "TypeScript Express-style app.listen on a framework object imported from express is a net.listen use, with a regression test"
bound = true
+++

Split from PKW7X2J. Not covered there: C# P/Invoke (cap-c02: DllImport/LibraryImport externs), general receiver typing beyond new T() bindings (typed parameters and fields calling instance methods such as HttpClient.GetAsync), Express-style app.listen on third-party framework objects, and DetectorEntry rows for typescript/csharp in grimble-model atoms.rs if a spelled-only detector is wanted.
