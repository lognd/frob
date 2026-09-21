# Unity toolchain guide

This is the shared home for Unity-specific documentation across several
tickets: T-4501 (editor detection, `frob doctor`), T-4508 (the batchmode
test-results evidence channel), and T-4509 (the capstone fixture/e2e proof
that scaffolding, asmdef modeling, dead-code detection, capability
scanning, and test collection all compose against a real Unity project).
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

## Pointing frob at an existing Unity project (T-4509)

frob understands a Unity project's own shape -- `.asmdef` assembly
boundaries, MonoBehaviour/coroutine lifecycle dispatch, the
`UnityEngine`/`UnityEditor` API surface, and NUnit/Unity Test Framework
test attributes -- well enough to point at an EXISTING Unity checkout
(one that already has `Assets/`/`Packages/`) and get real signal out of
`frob check`/capability scanning/test evidence, the same way it does for
a plain Python or C++ project. This section covers how to point frob at
your project, what gets detected, what capability findings to expect,
and how test evidence is gathered.

<!-- frob:describes src/frob/scaffold/_unity_project.py::render_unity_project -->
```bash
frob scaffold unity-project /path/to/MyUnityProject          # writes frob.toml + design/*.strata
frob scaffold unity-project /path/to/MyUnityProject --force  # overwrite an existing scaffold
```

Unlike every other `frob scaffold new <type> <name>` type, `unity-project`
scaffolds ONTO your existing project directory instead of creating a
fresh `<output_dir>/<name>/` tree -- there is no separate project name to
give it, only the directory. This writes:

- a starter `frob.toml` with Unity's own build-cache/meta excludes
  pre-populated (`Library/`, `Temp/`, `Logs/`, `obj/`, every `*.meta`
  file -- see `src/frob/excludes.py::UNITY_EXCLUDE_GLOBS`), so those
  never show up as tracked-file noise in `frob check`/`frob dup`/etc;
- one `design/<node_id>.strata` fragment per detected `.asmdef` (see
  "Asmdef component boundaries" below).

A directory with neither `Assets/` nor `Packages/` is refused with a
clear `NotAUnityProject` error, never a bogus config written. A second
run without `--force` is refused with `OutputExists` before anything is
written, so a refusal never leaves a partial scaffold behind.

If your frob build predates the `unity-project` CLI leaf, the same
result comes from calling the underlying function directly:

<!-- frob:describes src/frob/scaffold/_unity_project.py::render_unity_project -->
```python
from pathlib import Path
from frob.scaffold._unity_project import render_unity_project

render_unity_project(Path("/path/to/MyUnityProject"))
```

### Asmdef component boundaries

<!-- frob:describes src/frob/strata/_unity_asmdef.py::discover_asmdefs -->
<!-- frob:describes src/frob/strata/_unity_asmdef.py::build_component_nodes -->
Every `.asmdef` file under `Assets/`/`Packages/` becomes its own strata
component node (`code=<asmdef directory>/**`), with a `depends` edge for
each resolved `references` entry (by assembly name or by
`GUID:<hex>` resolved through the referencing asmdef's own `.meta`
sidecar), and an `is_editor_only` flag set when the asmdef's
`includePlatforms` is exactly `["Editor"]`. Unity's own implicit default
assembly -- every `.cs` file no asmdef's directory subtree covers -- is
always represented too, as a synthetic `unity_default_assembly` node, so
nothing silently falls outside the model. A two-asmdef project (say,
`Game.Runtime` and `Game.Tests`) always produces exactly three nodes:
the two asmdef nodes plus this catch-all.

### Dead-code detection: MonoBehaviour lifecycle and coroutines

<!-- frob:describes src/frob/lang/_walk_csharp.py::_cs_is_unity_entry_point -->
Unity invokes `Awake`/`Start`/`Update`/`FixedUpdate`/`LateUpdate`/
`OnEnable`/`OnDisable`/`OnDestroy`/the `OnCollision*`/`OnTrigger*` physics
callbacks, and any `IEnumerator`-returning coroutine method, through its
own component-message dispatch -- never a visible call site anywhere in
your own code. `frob check`'s dead-code detector (`DEAD001`, an
unreferenced PRIVATE symbol) treats every one of these as reachable
regardless of their own declared access modifier (a private, unmodified,
C#-default `void Update()` is marked public internally for exactly this
reason), so a genuine lifecycle method or coroutine is never flagged
dead code. A method decorated `[MenuItem(...)]` or `[InitializeOnLoad]`
(Unity Editor's own menu/domain-reload dispatch) gets the same exemption.

### Capability findings: what to expect

`UnityEngine`/`UnityEditor` API calls and .NET BCL calls in your scripts
resolve through frob's existing csharp capability scanner
(`frob.vet._capability_scan.scan_file_capabilities`) the same way any
other C# project's calls do. Notable Unity-specific rows:

| API | Capability kind | Notes |
|-----|-----------------|-------|
| `UnityWebRequest.Get/.Post/.Put`, `WWW`, `NetworkManager` | `net-connect` | Unity's own network-request/netcode surface |
| `Application.OpenURL` | `net-connect` AND `exec` | opens a URL through the platform handler -- both a network fetch and an arbitrary-handler-dispatch risk |
| `PlayerPrefs.SetString/.SetInt/.SetFloat/.Save` | `fs-write` | Unity's persistent, UNENCRYPTED local key-value store -- never store secrets here |
| `Resources.Load`, `Addressables.LoadAssetAsync` | `fs-read` | asset/content loading by a caller-supplied key/address |
| `AssetDatabase.CreateAsset/.DeleteAsset/.ImportAsset/.MoveAsset` | `fs-write` | Editor-tooling asset writes |
| any `UnityEditor.*` reference | `eval` | **editor-api-in-runtime fallback** -- see below |

**Editor-only API disclosed limitation.** The capability scanner works
off each file's raw text with no visibility into whether that file sits
under an `Editor/` folder or an Editor-only asmdef (`is_editor_only` in
the asmdef model above is a SEPARATE piece of information the scanner
does not currently consult). So a `UnityEditor.*` reference is flagged
under `eval` UNCONDITIONALLY, with `function_or_pattern` naming the
limitation directly ("editor-api-in-runtime: flagged unconditionally --
... a call genuinely made from real Editor tooling code is an expected,
benign hit here, not a defect"). Seeing this finding on a script that
genuinely lives in your `Editor/` folder is expected, not a false
positive; seeing it on a script that ships in a runtime build is the
real defect it is meant to catch (that reference fails to compile/load
there at all).

`frob vet`'s CLI scans your project's LOCKFILE dependencies (`uv.lock`/
`package-lock.json`/`Cargo.lock`/...), not your own first-party scripts
-- a Unity project ships none of those, so running the bare `frob vet`
CLI against one reports a clean `LockfileUnsupported` refusal, not a
capability finding. The capability table above comes from
`scan_file_capabilities` directly, the same primitive `frob vet`'s own
package scanner calls internally.

### Test evidence: NUnit and Unity Test Framework

<!-- frob:describes src/frob/testing/_collect_csharp.py::collect_csharp_tests -->
Every NUnit `[Test]`/`[TestCase(...)]`/`[TestCaseSource(...)]` and Unity
Test Framework `[UnityTest]` method under your project is collected as a
stable `<path>::<Namespace.Class>::<Method>` node id, by parsing `.cs`
source directly (no `dotnet`/Unity build required just to collect):

<!-- frob:describes src/frob/testing/_collect_csharp.py::collect_csharp_tests -->
```python
from pathlib import Path
from frob.testing._collect_csharp import collect_csharp_tests

result = collect_csharp_tests(Path("/path/to/MyUnityProject"))
for node_id in sorted(result.danger_ok.node_ids):
    print(node_id)
```

A `[TestCase(...)]`-parameterized method collapses to exactly one node
id (frob binds evidence to the source method, not to each runtime case
NUnit expands it into). `SetUp`/`TearDown`/`OneTimeSetUp`/
`OneTimeTearDown` are not test methods and are never collected.
Executing these tests (invoking `dotnet test`, or Unity's
`-batchmode -runTests` and parsing its NUnit3 XML results back onto
these same node ids) is a separate evidence-running channel tracked
under its own story -- collection above is what makes a test
`frob:tests`-bindable at all; running it is the next step once that
channel is available in your frob build.

### How the pieces compose

`tests/system/test_unity_e2e.py` (T-4509) is the checked-in proof that
all of the above compose end to end against a real fixture project
(`tests/fixtures/unity_sample/`): scaffolding succeeds and the asmdef
nodes match the fixture's `.asmdef` files, the fixture's MonoBehaviour
lifecycle method and coroutine are not flagged dead code, the fixture's
Editor-only API call and BCL/Unity API calls resolve to exactly the
expected capability findings with no unexpected ones on the fixture's
clean paths, and both a `[Test]` and a `[UnityTest]` method are
collected. Read that test file for a concrete, runnable example of every
step in this guide.
