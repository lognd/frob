+++
id = "01M65DW8H11TED28SHH942NFQ7"
title = "LOG: C# native function-pointer imports and Activator/Delegate reflection are not followed"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T03:32:55Z"
updated = "2026-10-30T03:32:55Z"
scope = ["crates/grimble-check/**", "docs/design/output-atoms.md"]
+++

Found while working ~4ENDA4R. NativeLibrary.GetExport, Marshal.GetDelegateForFunctionPointer, Activator.CreateInstance and Delegate.CreateDelegate resolve only as catalogue calls; the function or type they bind is not followed, and no Unresolved is reported when the target could be an output function.
