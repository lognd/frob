# C# docblock facet fixture (T-4510)

Two fenced `csharp` blocks proving `frob.gates._docblocks_refs.
_csharp_using_violations` (the `_CSHARP_LANGS` DOC004 bucket) resolves
against `Sample/Dup/Duplicate.cs` below the way the module docstring
describes -- both deliberately zero-violation, so `frob check`'s own
repo-wide DOC004 gate (which scans this file too) stays clean.
`tests/unit/test_support_csharp.py` builds the THIRD case -- the
unanchored block that fires an UNBOUND violation -- directly in memory
instead of sourcing it from a checked-in fenced block, precisely because
a real unanchored occurrence of this pattern in a real tracked `.md` file
is what DOC004 exists to catch; checking one in deliberately would fight
the gate this fixture is proving fires.

## Case 1: anchored project reference

A `using Sample.Dup;` block naming this project's own namespace (a
dotted prefix of the tracked `Sample/Dup/Duplicate.cs` path), with a
binding marker on the line immediately above the fence. Expected: zero
violations.

<!-- frob:doc tests/fixtures/csharp_dup_docblock/guide.md -->

```csharp
using Sample.Dup;
```

## Case 2: BCL reference, zero false positives

A `using System.Text;` block -- never resolves against any tracked
`.cs` path, so it is skipped outright regardless of anchoring. Expected:
zero violations even though no binding marker is nearby.

```csharp
using System.Text;
```
