"""`_UNITY_OPERATIONS`: Unity's own engine/editor API surface mapped onto
`_DangerousOperation` entries (T-4514, epic T-4513) -- a dedicated file
rather than an addition to `_dangerous_ops_bash_csharp.py`'s existing
csharp slice, per this ticket's own brief, because Unity's API surface is
a large, separately-evolving survey (its own namespace family:
`UnityEngine`/`UnityEngine.Networking`/`UnityEditor`/`Unity.Addressables`)
distinct from the general-purpose BCL idioms that file already curates
(`System.IO`/`System.Net`/`System.Diagnostics`) -- mirrors the existing
`_dangerous_ops_java.py`/`_dangerous_ops_cuda.py` precedent of "a new,
sufficiently-large library/platform family gets its own file" rather than
growing one already-large module past LARGE001.

Language is `"csharp"` throughout (Unity scripts ARE C#) -- this module
adds no new `LANGUAGES` entry, only new `library` values within the
existing csharp slice.

EDITOR-ONLY DISTINCTION -- disclosed limitation (T-4514 Done report):
the ticket's acceptance criterion asks for `UnityEditor.*` usage in a
runtime-code file (not under an `Editor/` folder or an Editor-only
asmdef) to read as a DISTINCT finding from the identical call made from
a real Editor script. `_DangerousOperation` (this registry's one entry
shape, `_schemas.py`) has no per-call FILE-PATH-CONDITIONAL field --
every entry is a flat (language, library, needle) -> capability_kind
row, evaluated purely against source TEXT by `frob.vet._capability`'s
needle scan, with no visibility into which directory the scanned file
lives under. `CAPABILITY_KINDS` (`_kinds.py`) is likewise a closed,
validated vocabulary with no "custom kind" escape hatch (`_validate_
registry_kinds` fails loudly on any kind used that is not registered
there) -- adding an ad hoc "editor-api-in-runtime" kind here would
silently diverge from that single source of truth.

Per the ticket brief's own explicit fallback ("otherwise flag as
capability 'eval' with a clear needle name and note the limitation"):
every `UnityEditor.*` entry below is registered once, unconditionally,
under `"eval"` (the closest existing kind to "in-repo authoring-time-only
code coupled outside its intended host process" -- an Editor API
compiled into a runtime build cannot execute correctly there at all,
the same class of hazard `"eval"` already covers for "code that should
never run in this context"), with `function_or_pattern` naming the
literal Editor surface so an audit finding reads unambiguously (never a
bare "eval" label). A TRUE per-file editor-vs-runtime split needs a
file-path-aware resolver (like `_capability_csharp.py`'s import-table
resolution, but keyed on the scanned file's own path/asmdef rather than
its using-directives) -- out of this ticket's declared scope
(`src/frob/vet/_capability_csharp.py` is NOT in T-4514's scope; T-4514's
Done report files the follow-up)."""

from __future__ import annotations

from frob.vet._capability_registry._schemas import _DangerousOperation, _op

_UNITY_OPERATIONS: tuple[_DangerousOperation, ...] = (
    # -- UnityEngine.Networking / legacy WWW / netcode (T-4514): every
    # network-request surface Unity ships, mapped like the BCL's own
    # HttpClient/WebClient entry in `_dangerous_ops_bash_csharp.py`.
    _op(
        "csharp",
        "UnityEngine.Networking",
        "UnityWebRequest.Get / .Post / .Put",
        "fetch_url",
        "issues an HTTP(S) request through Unity's own web-request client",
        "validate the target host and enforce TLS certificate validation; "
        "never build the URL from unsanitized user input",
        "medium",
        ("UnityWebRequest.Get(", "UnityWebRequest.Post(", "UnityWebRequest.Put("),
        (),
    ),
    # T-4554: the bare coarse "net" capability_kind these four entries
    # used is a RETIRED scanner kind -- no registry entry emits the
    # unqualified `net` vet-kind anymore (T-0771's net-connect/net-listen
    # split). Recategorized to `net-connect` -- the SAME precise kind
    # `_dotnet_bcl.py`'s outbound-network calls already use, and a
    # coarse `may "net"` declaration still covers `net-connect` exactly
    # as it covered the retired bare `net`, so no resolver behavior
    # change: only the raw scanner-kind bucket these needles land in
    # changes, from an unenforceable orphan to a drift-lock-accounted-for
    # one.
    _op(
        "csharp",
        "UnityEngine.Networking",
        "UnityWebRequest.Get / .Post / .Put (net)",
        "net-connect",
        "issues a network request through Unity's own web-request client",
        "validate the target host and enforce TLS certificate validation; "
        "never build the URL from unsanitized user input",
        "medium",
        ("UnityWebRequest.Get(", "UnityWebRequest.Post(", "UnityWebRequest.Put("),
        (),
    ),
    _op(
        "csharp",
        "UnityEngine",
        "WWW (legacy Unity web client)",
        "net-connect",
        "issues a network request through Unity's deprecated WWW class",
        "migrate to UnityWebRequest, which supports TLS validation and "
        "streaming this legacy class does not",
        "medium",
        ("new WWW(",),
        (),
    ),
    _op(
        "csharp",
        "UnityEngine.Networking",
        "NetworkManager (Unity multiplayer/netcode)",
        "net-connect",
        "starts or joins a multiplayer network session (host/client/"
        "server), opening inbound and/or outbound connections",
        "authenticate and validate every peer before trusting its "
        "payloads; never expose a NetworkManager on an untrusted interface "
        "without a transport-level allow-list",
        "medium",
        ("NetworkManager.Singleton", "new NetworkManager("),
        (),
    ),
    # -- Application.OpenURL (T-4514): opens the platform's default
    # handler for a URL/URI -- a network fetch (the browser/handler
    # resolves and loads it) AND a process-launch surface (a custom URI
    # scheme, e.g. `myapp://...` or `file://...`, can hand off to an
    # arbitrary registered handler), so it is registered under BOTH
    # `net-connect` and `exec` rather than picking one -- mirrors this
    # registry's existing "one API, two real risk axes -> two entries"
    # precedent (bash's curl|pipe-to-shell splits into `fetch_url` vs
    # `exec` rows). T-4554: `net` -> `net-connect`, same retired-bare-kind
    # fix as the three entries above.
    _op(
        "csharp",
        "UnityEngine",
        "Application.OpenURL (network fetch)",
        "net-connect",
        "opens a URL through the platform's default handler, an "
        "attacker-influenceable network fetch if the URL is not validated",
        "validate the URL's scheme and host against an allow-list before opening it",
        "medium",
        ("Application.OpenURL(",),
        (),
    ),
    _op(
        "csharp",
        "UnityEngine",
        "Application.OpenURL (arbitrary handler dispatch)",
        "exec",
        "hands off to whatever process/handler the platform registers for "
        "the URL's scheme (a custom URI scheme can launch an arbitrary "
        "registered application), not only a browser",
        "restrict accepted schemes to http/https and never pass a "
        "caller-influenced scheme through unchecked",
        "high",
        ("Application.OpenURL(",),
        ("CWE-78",),
    ),
    # -- PlayerPrefs (T-4514): Unity's own small persistent key-value
    # store (an INI/registry-backed file on most platforms) -- the
    # closest Unity analog of a local config/credential store, so it maps
    # onto the same fs-write/fs-read split `_dangerous_ops_bash_csharp.py`
    # already uses for `System.IO.File`'s write/read methods.
    _op(
        "csharp",
        "UnityEngine",
        "PlayerPrefs.SetString / .SetInt / .SetFloat / .Save",
        "fs-write",
        "writes a value into Unity's persistent, unencrypted local key-value store",
        "never store secrets/credentials in PlayerPrefs -- it is plain "
        "text on disk on most platforms; use platform secure storage "
        "instead",
        "medium",
        (
            "PlayerPrefs.SetString(",
            "PlayerPrefs.SetInt(",
            "PlayerPrefs.SetFloat(",
            "PlayerPrefs.Save(",
        ),
        ("CWE-312",),
    ),
    _op(
        "csharp",
        "UnityEngine",
        "PlayerPrefs.GetString / .GetInt / .GetFloat",
        "fs-read",
        "reads a value from Unity's persistent local key-value store",
        "treat any PlayerPrefs value as untrusted, attacker-writable "
        "input on a jailbroken/rooted device",
        "low",
        (
            "PlayerPrefs.GetString(",
            "PlayerPrefs.GetInt(",
            "PlayerPrefs.GetFloat(",
        ),
        (),
    ),
    # -- Asset/content loading (T-4514): Resources.Load, AssetDatabase's
    # read-side, and Addressables all resolve a caller-supplied string
    # key/path/address to packaged (or, for Addressables, REMOTE-catalog-
    # resolvable) content -- an `fs-read`-shaped surface, an unsanitized
    # key can traverse to an unintended asset or, for Addressables'
    # remote-catalog mode, an unintended remote source.
    _op(
        "csharp",
        "UnityEngine",
        "Resources.Load / Resources.LoadAsync",
        "fs-read",
        "loads a packaged asset by a caller-supplied path/key",
        "validate the key against an allow-listed set of expected asset "
        "paths rather than passing caller-supplied input straight through",
        "low",
        ("Resources.Load(", "Resources.LoadAsync("),
        (),
    ),
    _op(
        "csharp",
        "UnityEditor",
        "AssetDatabase.LoadAssetAtPath / .FindAssets / .LoadMainAssetAtPath",
        "fs-read",
        "reads an asset from the Editor's asset database by a "
        "caller-supplied path/query",
        "validate the path/query against the project's own Assets tree",
        "low",
        (
            "AssetDatabase.LoadAssetAtPath(",
            "AssetDatabase.FindAssets(",
            "AssetDatabase.LoadMainAssetAtPath(",
        ),
        (),
    ),
    _op(
        "csharp",
        "UnityEngine.AddressableAssets",
        "Addressables.LoadAssetAsync / .LoadAssetsAsync",
        "fs-read",
        "resolves and loads content by address, which for a remote "
        "catalog can fetch over the network from wherever that catalog "
        "currently points",
        "pin/verify the remote catalog's source and validate the address "
        "against an allow-listed set",
        "medium",
        ("Addressables.LoadAssetAsync(", "Addressables.LoadAssetsAsync("),
        (),
    ),
    # -- AssetDatabase write-side, and File usage specifically inside
    # Editor scripts (T-4514's own mapping): Editor tooling routinely
    # writes/deletes/imports project assets on disk -- `fs-write`, the
    # same kind `_dangerous_ops_bash_csharp.py` already uses for `System.
    # IO.File`'s write/delete methods; listed again here under the
    # `UnityEditor` library because these are Editor-namespace APIs, not
    # `System.IO` ones, so the csharp resolver's per-namespace wildcard
    # table (`_capability_csharp.py`'s `_CS_WILDCARD_DANGEROUS_NAMESPACES`)
    # would not otherwise resolve a bare `AssetDatabase.CreateAsset(...)`
    # call to a `System.IO` needle.
    _op(
        "csharp",
        "UnityEditor",
        "AssetDatabase.CreateAsset / .DeleteAsset / .ImportAsset / .MoveAsset",
        "fs-write",
        "creates, deletes, imports, or moves a project asset on disk from "
        "Editor tooling code",
        "scope the target path narrowly and confirm it is not "
        "attacker-influenced (e.g. from an untrusted import pipeline)",
        "high",
        (
            "AssetDatabase.CreateAsset(",
            "AssetDatabase.DeleteAsset(",
            "AssetDatabase.ImportAsset(",
            "AssetDatabase.MoveAsset(",
        ),
        ("CWE-732",),
    ),
    # -- UnityEditor.* general usage from a file NOT under an Editor/
    # folder or Editor-only asmdef (T-4514's editor-api-in-runtime
    # criterion) -- registered under the module docstring's disclosed
    # `"eval"` fallback (no file-path-conditional kind exists in this
    # registry). `function_or_pattern` names the limitation directly so
    # an audit finding never reads as a bare, unexplained "eval".
    _op(
        "csharp",
        "UnityEditor",
        "UnityEditor.* namespace usage (editor-api-in-runtime: flagged "
        "unconditionally -- this registry cannot see whether the scanned "
        "file sits under an Editor/ folder or an Editor-only asmdef; a "
        "call genuinely made from real Editor tooling code is an "
        "expected, benign hit here, not a defect)",
        "eval",
        "UnityEditor is an Editor-only assembly (System.Diagnostics.Process "
        "and code-execution-shaped APIs commonly appear alongside it in "
        "Editor tooling) -- referencing it from a script that ships in a "
        "runtime build fails to compile/load there at all",
        "move the referencing code into an Editor/ folder or an "
        'Editor-only asmdef (`"includePlatforms": ["Editor"]`), or '
        "guard it with #if UNITY_EDITOR",
        "medium",
        ("UnityEditor.",),
        (),
    ),
)
