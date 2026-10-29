+++
id = "01M64VBRNZ32N2JR6EYVVKBEKG"
title = "CAP: C# P/Invoke (DllImport) and typed instance-method receivers; TS Express app.listen"
type = "story"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-29T22:09:21Z"
updated = "2026-10-29T22:09:21Z"
scope = ["crates/gob-symbols/**", "crates/grimble-bind/**"]
+++

Split from PKW7X2J. Not covered there: C# P/Invoke (cap-c02: DllImport/LibraryImport externs), general receiver typing beyond new T() bindings (typed parameters and fields calling instance methods such as HttpClient.GetAsync), Express-style app.listen on third-party framework objects, and DetectorEntry rows for typescript/csharp in grimble-model atoms.rs if a spelled-only detector is wanted.
