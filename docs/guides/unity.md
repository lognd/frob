# Unity toolchain guide

This is the shared home for Unity-specific documentation across several
tickets: T-4501 (editor detection, `frob doctor`), T-4508 (the batchmode
test-results evidence channel), and T-4509 (its own future addition).
Kept short and CLI-first -- design rationale lives in the code's own
docstrings.

## Locating the Unity Editor (T-4501)

`frob doctor` locates an installed Unity Editor, in precedence order:

1. `UNITY_PATH` or `UNITY_EDITOR` environment variable (an explicit path
   to the editor binary).
2. Unity Hub's default per-OS install root (the newest installed version
   directory wins when several are present).
3. A plain PATH lookup for `Unity`/`unity`.

See `install.md`'s "Unity toolchain detection (T-4501)" section for full
detail on this search.

## Unity batchmode evidence channel

`frob.testing._unity_batchmode.run_unity_batchmode` runs a selected set of
`[Test]`/`[UnityTest]` node ids (the same
`<path>::<Namespace.Class>::<Method>` shape T-4517's csharp collector
produces) through the Unity Editor's batchmode test runner, and parses the
resulting NUnit3 XML report into a per-test pass/fail map.

The exact CLI invocation, for reference (and for anyone reproducing a run
by hand):

```sh
Unity -batchmode -runTests \
    -projectPath <path/to/unity/project> \
    -testResults <path/to/results.xml> \
    -testFilter <Namespace.Class.Method>[,<Namespace.Class.Method>...] \
    -quit
```

- `-testResults` is always a fresh, not-yet-existing path -- Unity writes
  the NUnit3 report there when the run completes (however it completes).
- `-testFilter` is a comma-separated list of dotted fully-qualified test
  names (`Namespace.Class.Method`, NOT frob's own `::`-delimited node id
  shape); omit it to run the whole suite.
- A run that exits non-zero AND leaves no results file at `-testResults`
  is treated as an editor crash or license failure -- a distinct, clearly
  labeled error (`UnityBatchmodeError.RunFailed`), never a silent
  "zero tests ran, zero tests failed" false pass.

### Resolving the editor for this channel

`resolve_unity_editor(root)` picks the editor binary to invoke, in
precedence order:

1. `[tool.frob] unity_editor` in `root/pyproject.toml` -- an explicit,
   repo-pinned override, e.g.:

   ```toml
   [tool.frob]
   unity_editor = "/opt/Unity/Hub/Editor/2022.3.5f1/Editor/Unity"
   ```

2. `frob doctor`'s own T-4501 lookup (`UNITY_PATH`/`UNITY_EDITOR`, Unity
   Hub's default root, then PATH) -- reused, not re-implemented.

### Result mapping

NUnit3's `<test-case fullname="..." result="...">` leaves are matched
back to a requested node id by dotted fully-qualified name
(`Namespace.Class.Method`, derived from the node id by dropping its
leading `<path>::` segment and joining the remaining two `::`-separated
segments with a dot). A requested node id with no matching `test-case` in
the parsed report is a hard error
(`UnityBatchmodeError.ResultsUnreadable`), never a silently-omitted
result -- the same "never a silent empty-results false pass" rule the
crash-handling case above applies.

<!-- frob:describes src/frob/testing/_unity_batchmode.py::UnityBatchmodeError -->
<!-- frob:describes src/frob/testing/_unity_batchmode.py::parse_unity_batchmode_xml -->
<!-- frob:describes src/frob/testing/_unity_batchmode.py::resolve_unity_editor -->
<!-- frob:describes src/frob/testing/_unity_batchmode.py::run_unity_batchmode -->

