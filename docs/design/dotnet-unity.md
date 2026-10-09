# C#, .NET and Unity support (D94)

Status: current
Owner: grimble
Decisions: D94
Audience: contributor

Provenance: accepted direction, owner request 2026-10-05: run frob on the
owner's project-hullbreach repositories. `game` is a Unity 6 project
(6000.0.43f1, URP, Input System): 129 C# files in 17 assembly
definitions, 274 NUnit `[Test]` and 17 `[UnityTest]` tests through the
Unity Test Framework, MonoBehaviour messages (`Awake`, `Update`,
`FixedUpdate`, `LateUpdate`, `OnDestroy`, ...), shaders. `platform` is
Python with some TS/TSX and CSS and a `crunk.toml`. Both run frob v1
today. Python is covered by the first-party adapter (epic ~HKNM4VV);
TS/TSX and CSS ingest is crunk's 0.537.0 work. This design adds the
missing piece: C#, the .NET project model, and Unity's engine contract.

## 1. Layers

| Layer | What | Where |
|---|---|---|
| Language | C# grammar, comments, symbols, imports, calls, attributes, XML doc comments, test detection | gob-languages, gob-symbols (first-party adapter, same fidelity bar as Rust and Python, code-model.md) |
| Project model | which files form one assembly and what it references: `.sln` and `.csproj` for .NET, `.asmdef` and `.asmref` for Unity (Unity generates `.csproj` files and they are not committed) | gob-symbols project discovery, mapped to the existing package/unit notion so ownership, reach and test selection work unchanged |
| Engine vocabulary | the Unity contract: which methods the engine calls, which fields the editor writes, which calls are dynamic | a `unity` vocabulary pack (packs.md, D76), opt-in, auto-suggested by `frob init` when `ProjectSettings/ProjectVersion.txt` exists |
| Test runners | `dotnet test` (TRX) and Unity's test runner in batch mode (NUnit 3 XML) | frob-evidence providers `dotnet` and `unity`, frob test selection |

Project model details (implemented in `unity_project.rs`): a package per
`.asmdef` with `name`, `references` (name or `GUID:`), `includePlatforms`,
`excludePlatforms`, `defineConstraints`, `precompiledReferences`,
`overrideReferences`, `autoReferenced` and `allowUnsafeCode`; an assembly is
editor-only when `includePlatforms` is `[Editor]`, and a test assembly when it
has `UNITY_INCLUDE_TESTS` and a `UnityEngine.TestRunner` reference, with mode
decided by a `PlayMode` or `EditMode` path segment, else editor-only means
EditMode and anything else PlayMode. Implicit assemblies reference every
auto-referenced asmdef (and the editor variants the runtime ones). Unresolved
GUIDs, malformed definitions and dangling `.asmref`s are findings.

Nothing here is Unity-specific below the vocabulary pack: plain .NET
repositories get the language, project model and `dotnet` provider
without it.

## 2. The C# adapter

Grammar: tree-sitter-c-sharp, pinned like the other grammars. Units:
namespaces (file-scoped and block), types (class, struct, record,
interface, enum, delegate), members (methods, constructors, properties,
indexers, events, fields, operators, local functions); partial types
merge into one unit with several spans. Imports: `using`, `using
static`, aliases, global usings. Calls: invocations with qualifiers,
extension methods resolved where the receiver type is known, otherwise
Unresolved (never clean). Attributes become attributes on the unit.
`///` XML doc comments feed the DOC rules. Test detection: NUnit
(`[Test]`, `[TestCase]`, `[TestCaseSource]`, `[UnityTest]`), xUnit
(`[Fact]`, `[Theory]`) and MSTest (`[TestMethod]`); a test id is the
fully qualified method name, the form both runners filter by.
Preprocessor symbols (`#if UNITY_EDITOR`): both branches are scanned
and units carry the condition, so editor-only code is not reported as
dead in player builds or the reverse.

## 3. The Unity vocabulary

- Engine entry points are reach roots: MonoBehaviour and
  ScriptableObject messages (`Awake`, `Start`, `Update`, `FixedUpdate`,
  `LateUpdate`, `OnEnable`, `OnDisable`, `OnDestroy`, `OnValidate`,
  `OnTrigger*`, `OnCollision*`, `OnGUI`, ...) on types deriving from
  those bases, plus `[RuntimeInitializeOnLoadMethod]`,
  `[InitializeOnLoad]`, `[MenuItem]`, `[ContextMenu]`. Coverage and
  reach rules treat them as called by the engine, not as dead code.
- Editor-written state: `[SerializeField]` and public serialized fields
  are written from outside the code (scenes, prefabs, the Inspector);
  effect and flow rules see an external writer.
- Dynamic dispatch: `SendMessage`, `Invoke("name")`, `UnityEvent`
  wiring in assets and string-keyed lookups are dynamic calls, reported
  Unresolved per the compute policy, never resolved by guesswork.
- Asset hygiene: every tracked file under `Assets/` and `Packages/` has
  its `.meta`, and no `.meta` is orphaned; a duplicate GUID is an error.
  This is a small UNITY rule family in the pack.
- Out of scope at first: scene and prefab YAML contents beyond GUID
  references, ShaderLab and HLSL (opaque F0 files, as today).

## 4. Evidence and test selection

`dotnet` provider: runs `dotnet test --logger trx` with a filter built
from test ids, parses TRX per test, through gob-exec and the shared
redact, scrub and escape paths, allowlisted like pytest. `unity`
provider: runs the Unity editor in batch mode
(`-batchmode -runTests -testPlatform EditMode|PlayMode -testResults`
with `-testFilter`), parses the NUnit 3 XML. The editor path comes from
config (`[evidence.unity] editor`), defaulting to the version in
`ProjectSettings/ProjectVersion.txt` under the standard Unity Hub
install locations; a missing editor or license refuses with a remedy,
never a silent skip. PlayMode tests need a graphics-less runner flag
and are slower; the provider runs EditMode by default and PlayMode when
the selected tests need it. `frob test` maps touched C# symbols to test
ids through the same reach graph as Rust and Python.

## 5. Sequencing

1. C# language and symbols (adapter, fixtures, fidelity row), and the
   `.csproj`/`.asmdef` project model.
2. `dotnet` evidence provider and C# test selection.
3. The `unity` vocabulary pack (entry points, serialized fields,
   dynamic calls, `.meta` hygiene).
4. The `unity` evidence provider (needs a Unity editor; proven on the
   owner's Windows side through goway, one run at a time).
5. Migrate project-hullbreach `game` and `platform` from frob v1 to v2
   (migration.md) and run them as the post-0.532.0 real-world trial.
