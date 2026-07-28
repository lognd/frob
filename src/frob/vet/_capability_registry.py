"""Single-source dangerous-operations registry (T-0158): one authoritative
enumeration of every reserved capability kind, plus the structured
dangerous-operation entries `frob.vet._capability` compiles into its
per-language needle tables. Every consumer of "what capability kinds
exist" -- `frob.vet._capability`, `frob.strata._threat`'s `CWE_CATALOG`/
`CWE_TOP_25_CATALOG`/`DEFAULT_BENIGN_CAPABILITIES`, `frob.strata._effects`'s
`_KIND_MAP`, the surface grammar's `may` atoms -- imports `CAPABILITY_KINDS`
from HERE so the vocabulary cannot fork (extends the T-0150 drift-lock:
`_validate_registry_kinds` fails loudly if any consumer uses a kind absent
from this tuple).

Addendum 1 (2026-07-18) promotes every `_PATTERNS` needle into a
`_DangerousOperation`: {language, library, function_or_pattern,
capability_kind, cwe_links, rationale, safer_alternative, severity} --
audit findings then name the registry entry instead of a bare kind label.

Addendum 2 (2026-07-18) demands EXHAUSTIVE, CLOSED-WORLD coverage: every
stdlib module that can touch process/fs/net/env/dynamic-code is curated
here (see `NO_CAPABILITY_MODULES` for the pure side of that curation), and
`CAPABILITY_MATRIX_EXCUSES` replaces the old blanket C/C++ "honestly-
empty" exemption with a per-(kind, language) decision: every cell is
EITHER patterned (>=1 `_DangerousOperation`) OR excused with a specific
written reason (`OutOfScopeEntry`-style discipline, docs/modules/vet.md
"Coverage matrix").

T-0181 (addendum 2 remainder, 2026-07-18) drains the addendum 2 priority
survey list -- python (pydantic/fastapi/numpy/cryptography/jinja2/
python-dotenv/uvicorn/sqlalchemy/asyncpg/alembic/redis/boto3/stripe/
anthropic/argon2-cffi/aiosmtpd/playwright/Pillow), npm (react/react-dom/
vite/vitest/playwright/openapi-typescript/eslint tooling), and cargo
(pyo3/serde/serde_json/tracing/libloading/wasm-bindgen/crossbeam/
thiserror) -- against each library's real API surface: each library ends
as either new `_DangerousOperation` entries below or is a pure library with
no dangerous surface (documented in docs/modules/vet.md "Third-party
library survey (T-0181)", not silently dropped).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/vet/_capability_registry.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/vet.md#public-api
#: every language the matrix reasons about. C and C++ share one bucket
#: (`c-cpp`) since the dangerous idioms -- `system`/`popen`/`exec*`/
#: `dlopen`/`strcpy`-family -- are identical C ABI surface in both.
LANGUAGES: tuple[str, ...] = ("python", "typescript", "rust", "c-cpp", "kotlin")

# frob:doc docs/modules/vet.md#public-api
#: SINGLE-SOURCE enumeration of every reserved capability kind (T-0158).
#: Union of: every `capability_kind` `frob.strata._threat.CWE_CATALOG`/
#: `CWE_TOP_25_CATALOG` names, every kind `DEFAULT_BENIGN_CAPABILITIES`
#: excuses, and every kind this registry's `_DangerousOperation` table
#: patterns. Any kind used anywhere else that is NOT in this tuple is a
#: drift bug -- `_validate_registry_kinds` (below) is the loud failure.
CAPABILITY_KINDS: tuple[str, ...] = (
    "exec",
    "eval",
    "net",
    "fs-write",
    #: `frob.strata._effects._KIND_MAP` normalizes the scanner's `fs-write`
    #: spelling to `fs` for the tier-2 `may`-declaration vocabulary (net/
    #: fs-write/exec are the three delegated kinds); `DEFAULT_BENIGN_
    #: CAPABILITIES` excuses THAT normalized spelling, not the raw scanner
    #: token, so both live in this registry.
    "fs",
    #: T-0018 (graphite adoption): a node whose code ONLY reads local
    #: filesystem state (config loads, e.g. `Path.read_text()`/
    #: `json.loads()`) could never satisfy SYS101 declaring `may "fs"` --
    #: the scanner only ever emitted the write-derived "fs"/"fs-write"
    #: kinds, forcing a `waive "SYS101:fs"` for genuinely-real read-only
    #: access. `fs-read` is a NEW, separate observed kind (not an alias of
    #: "fs"); `frob.strata._selfconform`'s SYS101 join treats a bare `may
    #: "fs"` declaration as backward-compatibly satisfied by EITHER
    #: observed kind (a pre-existing "fs" declaration should not go stale
    #: just because the only real access turns out to be reads), while a
    #: node that declares `may "fs-read"` specifically gets the honest,
    #: narrower signal (docs/strata/selfconform.md#fs-read-fs-write).
    "fs-read",
    "env",
    "ffi",
    "install-hook",
    "html_render",
    "sql",
    "fetch_url",
    "deserialize",
    "client_storage",
    #: T-0244: a large HTML/JS-shaped STRING LITERAL embedded in another
    #: language's source (the malmberg pilot P3 shape -- a 5400-line
    #: dashboard's markup/script sitting inside a Python string) is
    #: structurally invisible to every per-language needle table above,
    #: which only ever scans a file's OWN source grammar. `frob.vet.
    #: _capability._embedded_code_regions` detects such a region (size +
    #: HTML/JS signal heuristic) and always emits this kind for the region
    #: it found, independent of whether the embedded needle re-scan below
    #: (typescript table over the region's own text) turns up anything
    #: specific -- fail-closed per docs/design/structural-linter-
    #: adversarial-hardening.md rule 3: the region is DECLARED, never
    #: silently passed, even when the best-effort re-scan is empty.
    "embedded_code",
)


# T-0524: frob:doc removed -- DANGEROUS_OPERATIONS (public, below) already
# carries both the same docs/modules/vet.md#public-api anchor and the
# extending-guide anchor (COV007: a private schema class does not need
# its own copy of the doc edge its public constant already carries).
class _DangerousOperation(BaseModel):
    """One structured dangerous-operation entry (T-0158 addendum 1):
    a single builtin/stdlib/library function or literal pattern that
    grants `capability_kind`, with enough metadata (`cwe_links`,
    `rationale`, `safer_alternative`, `severity`) that an audit finding
    can name WHY it fired and what to do instead, not just a bare kind
    label."""

    model_config = ConfigDict(frozen=True)

    language: str
    library: str
    function_or_pattern: str
    capability_kind: str
    cwe_links: tuple[str, ...] = ()
    rationale: str
    safer_alternative: str
    severity: str  # "low" | "medium" | "high" | "critical"
    #: literal substring needle(s) `frob.vet._capability` matches against
    #: raw source text -- kept separate from `function_or_pattern` (the
    #: human-facing name) so a needle can differ cosmetically (e.g. a
    #: trailing `(` to avoid partial-identifier false positives).
    needles: tuple[str, ...] = ()


# T-0524: frob:doc removed -- CAPABILITY_MATRIX_EXCUSES (public, below)
# already carries the same docs/modules/vet.md#public-api anchor (COV007).
class _MatrixExcuse(BaseModel):
    """A written, specific reason a (kind, language) cell has NO
    `_DangerousOperation` entries -- T-0158 retires the old blanket C/C++
    exemption; every excused cell names its own missing idiom, never a
    boilerplate 'not applicable'."""

    model_config = ConfigDict(frozen=True)

    capability_kind: str
    language: str
    reason: str


def _op(
    language: str,
    library: str,
    function_or_pattern: str,
    capability_kind: str,
    rationale: str,
    safer_alternative: str,
    severity: str,
    needles: tuple[str, ...],
    cwe_links: tuple[str, ...] = (),
) -> _DangerousOperation:
    """Terse constructor so the table below reads as data, not boilerplate."""
    return _DangerousOperation(
        language=language,
        library=library,
        function_or_pattern=function_or_pattern,
        capability_kind=capability_kind,
        cwe_links=cwe_links,
        rationale=rationale,
        safer_alternative=safer_alternative,
        severity=severity,
        needles=needles,
    )


# frob:doc docs/modules/vet.md#public-api
# frob:doc docs/guides/extending/capability-registry.md#capability-registry
# frob:ticket T-0158
# frob:waive SCOPE001 reason="T-0706's declared scope is docs/design/registry/check-coverage.yaml+docs/guides/extending/**+the two drift-lock test files; this one-line anchor restore is the actual root cause tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete.test_every_row_anchor_file_exists_and_mentions_guide/test_every_anchor_fragment_resolves_to_guide_h1 need to pass (T-0524 over-pruned this anchor as a false COV007 duplicate in 2642c5f3) -- same ad-hoc precedent as tests/test_check_coverage_registry.py's existing T-0424 SCOPE001 waiver"  # noqa: E501
DANGEROUS_OPERATIONS: tuple[_DangerousOperation, ...] = (
    # -- python: process/exec ------------------------------------------------
    _op(
        "python",
        "subprocess",
        "subprocess.run/Popen/call/check_output",
        "exec",
        "spawns an external process with the current process's privileges",
        "avoid shelling out; if unavoidable, use an argv list (never shell=True) "
        "and validate every argument",
        "high",
        # "Popen(" restored (reviewer finding): the pre-T-0158 table caught
        # `from subprocess import Popen; Popen(cmd)` -- no `subprocess.`
        # prefix at the call site -- via a bare "Popen(" needle. Losing it
        # in the registry migration was a silent detection regression on
        # the most common bare-import spawn idiom. Case-sensitive substring
        # match: distinct from c-cpp's lowercase "popen(" needle (T-0151
        # word-boundary precedent already applies there via that entry's
        # own needle, not this one) -- "Popen(" cannot collide with
        # "popen(" since Python `str.find`/`in` are case-sensitive.
        ("subprocess.", "Popen("),
        ("CWE-78",),
    ),
    _op(
        "python",
        "os",
        "os.system/os.popen/os.exec*",
        "exec",
        "delegates to the shell or replaces the process image with attacker-"
        "influenceable input",
        "use subprocess.run with an argv list",
        "high",
        ("os.system(", "os.popen(", "os.exec"),
        ("CWE-78",),
    ),
    _op(
        "python",
        "os",
        "os.spawn*",
        "exec",
        "spawns a child process, shell-adjacent to the exec* family",
        "use subprocess.run with an argv list",
        "medium",
        ("os.spawn",),
        ("CWE-78",),
    ),
    # -- python: dynamic code / deserialization -------------------------------
    _op(
        "python",
        "builtins",
        "eval()/exec()",
        "eval",
        "executes an arbitrary string as Python code",
        "never evaluate untrusted input; use ast.literal_eval for data-only parsing",
        "critical",
        ("eval(", "exec("),
        ("CWE-95",),
    ),
    _op(
        "python",
        "builtins",
        "compile() (bare builtin call)",
        "eval",
        "turns a code string into a code object for later eval/exec; eval-"
        "adjacent primitive (T-0151)",
        "avoid compiling untrusted source",
        "high",
        (),
        ("CWE-95",),
    ),
    _op(
        "python",
        "builtins",
        "__import__()",
        "eval",
        "imports a module named by a runtime string, letting untrusted input "
        "choose what code loads",
        "use a static import or a vetted allowlist-driven importlib.import_module",
        "high",
        ("__import__(",),
        ("CWE-829",),
    ),
    _op(
        "python",
        "importlib",
        "importlib.import_module()",
        "eval",
        "imports a module named by a runtime string",
        "validate the module name against an explicit allowlist first",
        "medium",
        ("importlib.import_module(",),
        ("CWE-829",),
    ),
    _op(
        "python",
        "importlib",
        "importlib.util.spec_from_file_location",
        "eval",
        "loads and executes an arbitrary file's source as a module",
        "only load modules from a trusted, fixed path set",
        "high",
        ("spec_from_file_location(",),
        ("CWE-829",),
    ),
    _op(
        "python",
        "runpy",
        "runpy.run_path/run_module",
        "eval",
        "executes an arbitrary file or module by name at runtime",
        "avoid dynamic entry-point resolution for untrusted input",
        "high",
        ("runpy.run_path(", "runpy.run_module("),
        ("CWE-95",),
    ),
    _op(
        "python",
        "code",
        "code.InteractiveInterpreter/compile_command",
        "eval",
        "builds an interactive Python evaluator over runtime input",
        "never expose an interactive interpreter to untrusted input",
        "critical",
        ("code.InteractiveInterpreter", "code.compile_command("),
        ("CWE-95",),
    ),
    _op(
        "python",
        "pickle",
        "pickle.load/loads",
        "deserialize",
        "unpickling untrusted data can execute arbitrary code via __reduce__",
        "use a data-only format (json) or hmac-sign the pickle payload",
        "critical",
        ("pickle.load(", "pickle.loads("),
        ("CWE-502",),
    ),
    _op(
        "python",
        "marshal",
        "marshal.load/loads",
        "deserialize",
        "unmarshalling untrusted bytecode-adjacent data is unsafe by design",
        "never marshal untrusted input; it is a private interpreter format",
        "high",
        ("marshal.load(", "marshal.loads("),
        ("CWE-502",),
    ),
    _op(
        "python",
        "shelve",
        "shelve.open",
        "deserialize",
        "shelve is pickle-backed; opening an untrusted shelf file deserializes "
        "attacker-controlled pickle data",
        "use sqlite3 or a data-only store for untrusted-origin files",
        "high",
        ("shelve.open(",),
        ("CWE-502",),
    ),
    # -- python: FFI / dynamic loading ---------------------------------------
    _op(
        "python",
        "ctypes",
        "ctypes.CDLL/cdll/windll",
        "ffi",
        "loads and calls into arbitrary native code, bypassing Python's memory safety",
        "avoid loading native libraries from untrusted or writable paths",
        "high",
        ("ctypes.", "import ctypes"),
        (),
    ),
    _op(
        "python",
        "cffi",
        "cffi.FFI",
        "ffi",
        "same native-code boundary as ctypes via the cffi bridge",
        "avoid loading native libraries from untrusted or writable paths",
        "high",
        ("cffi",),
        (),
    ),
    # T-0222 (sibling-pilot P1 gap 5): a compiled/native extension import
    # (a pyo3-built .so, a plain C-extension module) is real FFI surface
    # that ctypes/cffi's needles above never see -- `import strata_core`
    # (this very repo's own native binding) is ordinary Python import
    # syntax, indistinguishable by substring from a pure-Python import.
    # `importlib.machinery.ExtensionFileLoader` is the one unambiguous
    # stdlib literal naming "this is a compiled extension module loader"
    # (used by CPython's own import machinery, and by any code that loads
    # a `.so`/`.pyd` extension module explicitly) -- narrow, no known
    # false-positive class (unlike a bare `.so`/`.pyd` substring, which
    # would fire on prose mentioning shared-library files).
    _op(
        "python",
        "importlib",
        "importlib.machinery.ExtensionFileLoader",
        "ffi",
        "explicitly loads a compiled/native extension module (.so/.pyd), "
        "the same native-code memory-safety boundary as ctypes/cffi",
        "prefer the ordinary import system for known-trusted packages; "
        "only use ExtensionFileLoader directly for a vetted, pinned "
        "native extension path",
        "high",
        ("ExtensionFileLoader",),
        (),
    ),
    # -- python: net -----------------------------------------------------------
    _op(
        "python",
        "socket",
        "socket.socket/create_connection",
        "net",
        "opens a raw network socket",
        "prefer a higher-level client with TLS verification enabled",
        "medium",
        ("socket.",),
        (),
    ),
    _op(
        "python",
        "http.client",
        "http.client.HTTPConnection",
        "net",
        "issues raw HTTP requests, stdlib low-level client",
        "prefer httpx/requests with a pinned timeout and cert verification",
        "low",
        ("http.client",),
        (),
    ),
    # RECLASSIFIED (reviewer diff-audit): the pre-T-0158 table put the bare
    # "urllib." needle under python/net. This registry moves it to
    # fetch_url instead -- urlopen's actual danger is SSRF (CWE-918, the
    # catalog's dedicated fetch_url kind), a strictly MORE PRECISE
    # classification than the old generic net bucket, not a coverage loss:
    # the needle still fires, just under the more specific kind.
    _op(
        "python",
        "urllib",
        "urllib.request.urlopen",
        "fetch_url",
        "fetches a URL that may be attacker-influenced (SSRF surface)",
        "validate/allowlist the target host before fetching",
        "medium",
        ("urllib.",),
        ("CWE-918",),
    ),
    _op(
        "python",
        "ftplib",
        "ftplib.FTP",
        "net",
        "opens a plaintext FTP control/data connection",
        "prefer SFTP/FTPS with certificate verification",
        "low",
        ("ftplib.",),
        (),
    ),
    _op(
        "python",
        "smtplib",
        "smtplib.SMTP",
        "net",
        "opens an outbound SMTP connection, potential mail-relay abuse surface",
        "restrict SMTP host/credentials to a trusted, configured relay",
        "low",
        ("smtplib.",),
        (),
    ),
    _op(
        "python",
        "requests",
        "requests.get/post/...",
        "net",
        "third-party HTTP client issuing outbound requests",
        "pin a timeout and verify=True; validate SSRF-sensitive URLs",
        "medium",
        ("requests.",),
        (),
    ),
    _op(
        "python",
        "aiohttp",
        "aiohttp.ClientSession",
        "net",
        "third-party async HTTP client issuing outbound requests",
        "pin a timeout and verify SSL; validate SSRF-sensitive URLs",
        "medium",
        ("aiohttp.",),
        (),
    ),
    _op(
        "python",
        "httpx",
        "httpx.Client/get/post",
        "net",
        "third-party HTTP client issuing outbound requests",
        "pin a timeout and verify=True; validate SSRF-sensitive URLs",
        "medium",
        ("httpx.",),
        (),
    ),
    _op(
        "python",
        "webbrowser",
        "webbrowser.open",
        "exec",
        "launches the system's default browser/handler for a URL, an OS-level "
        "process-spawn analog",
        "validate the URL scheme/host before opening",
        "low",
        ("webbrowser.open(",),
        (),
    ),
    _op(
        "python",
        "asyncio",
        "asyncio.create_subprocess_exec/shell",
        "exec",
        "spawns an external process via the asyncio event loop",
        "use create_subprocess_exec with an argv list, never *_shell",
        "high",
        ("create_subprocess_exec(", "create_subprocess_shell("),
        ("CWE-78",),
    ),
    _op(
        "python",
        "asyncio",
        "asyncio.open_connection/start_server",
        "net",
        "opens an async network socket",
        "prefer a higher-level client with TLS verification enabled",
        "medium",
        ("asyncio.open_connection(", "asyncio.start_server("),
        (),
    ),
    # -- python: fs-write --------------------------------------------------
    _op(
        "python",
        "builtins",
        "open() (write/append mode)",
        "fs-write",
        "writes/overwrites local filesystem state",
        "validate the target path is inside an expected root before writing",
        "low",
        ("open(", ".write("),
        ("CWE-22",),
    ),
    _op(
        "python",
        "os",
        "os.remove/os.rename",
        "fs-write",
        "mutates or removes local filesystem state",
        "validate the target path is inside an expected root before mutating",
        "medium",
        ("os.remove(", "os.rename("),
        ("CWE-22",),
    ),
    _op(
        "python",
        "shutil",
        "shutil.rmtree/move/copy",
        "fs-write",
        "recursively mutates/removes a filesystem tree",
        "validate the target path is inside an expected root; never rmtree a "
        "caller-supplied path",
        "high",
        ("shutil.rmtree(", "shutil.move(", "shutil.copy("),
        ("CWE-22",),
    ),
    _op(
        "python",
        "pathlib",
        "Path.write_text/write_bytes/unlink",
        "fs-write",
        "mutates or removes local filesystem state via the pathlib API",
        "validate the target path is inside an expected root before writing",
        "low",
        ("write_text(", "write_bytes(", ".unlink("),
        ("CWE-22",),
    ),
    # -- python: fs-read (T-0018, graphite adoption) ------------------------
    _op(
        "python",
        "pathlib",
        "Path.read_text/read_bytes",
        "fs-read",
        "reads local filesystem state (e.g. a config file)",
        "validate the source path is inside an expected root before reading",
        "low",
        ("read_text(", "read_bytes("),
        (),
    ),
    _op(
        "python",
        "builtins/json",
        "open() (read mode) / json.load",
        "fs-read",
        "reads local filesystem state via the builtin file API or the json "
        "stdlib module",
        "validate the source path is inside an expected root before reading",
        "low",
        ("json.load(",),
        (),
    ),
    _op(
        "python",
        "tempfile",
        "tempfile.mktemp",
        "fs-write",
        "creates a predictable temp path with a TOCTOU race window (unlike mkstemp)",
        "use tempfile.mkstemp/NamedTemporaryFile instead of mktemp",
        "medium",
        ("tempfile.mktemp(",),
        (),
    ),
    _op(
        "python",
        "sqlite3",
        "cursor.execute() with string-formatted SQL",
        "sql",
        "string-interpolated SQL is injectable if any operand is untrusted",
        "use parameterized queries (execute(sql, params))",
        "high",
        ('execute(f"', "execute('%s'", 'execute(" +'),
        ("CWE-89",),
    ),
    # -- python: env / process introspection ---------------------------------
    _op(
        "python",
        "os",
        "os.environ / os.getenv",
        "env",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("os.environ", "os.getenv("),
        (),
    ),
    _op(
        "python",
        "sys",
        "sys.exit / os._exit",
        "env",
        "terminates the process; low-severity but part of the exhaustive "
        "process-control surface",
        "prefer raising and letting the entry point decide the exit code",
        "low",
        ("os._exit(",),
        (),
    ),
    _op(
        "python",
        "signal",
        "signal.signal",
        "env",
        "installs a process-wide signal handler",
        "keep signal handlers minimal and audited",
        "low",
        ("signal.signal(",),
        (),
    ),
    _op(
        "python",
        "pty",
        "pty.spawn/fork",
        "exec",
        "spawns a process attached to a pseudo-terminal, full interactive "
        "process-control surface",
        "avoid pty.spawn on untrusted commands",
        "high",
        ("pty.spawn(", "pty.fork("),
        ("CWE-78",),
    ),
    _op(
        "python",
        "multiprocessing",
        "multiprocessing.Process/Pool",
        "exec",
        "spawns a child process (or process pool) with the parent's privileges",
        "validate the target callable/args come from trusted code",
        "low",
        ("multiprocessing.Process(", "multiprocessing.Pool("),
        (),
    ),
    _op(
        "python",
        "platform",
        "os.startfile / platform exec paths",
        "exec",
        "invokes the OS default handler for a path, a process-spawn analog",
        "validate the path before invoking the OS handler",
        "medium",
        ("os.startfile(",),
        (),
    ),
    _op(
        "python",
        "setuptools",
        "cmdclass= packaging install hook",
        "install-hook",
        "a custom setuptools cmdclass runs arbitrary code at install time",
        "avoid custom install-time hooks; use declarative build config",
        "medium",
        ("cmdclass",),
        (),
    ),
    # -- typescript/js: exec --------------------------------------------------
    _op(
        "typescript",
        "child_process",
        "exec/execSync/spawn/execFile",
        "exec",
        "spawns an external process, exec() variants go through a shell",
        "use execFile/spawn with an argv array, never exec() with untrusted input",
        "high",
        ("child_process", "execSync(", "spawn(", "execFile("),
        ("CWE-78",),
    ),
    # -- typescript/js: eval ----------------------------------------------
    _op(
        "typescript",
        "builtins",
        "eval() / new Function()",
        "eval",
        "executes an arbitrary string as JavaScript",
        "never evaluate untrusted input",
        "critical",
        ("eval(", "new Function("),
        ("CWE-95",),
    ),
    _op(
        "typescript",
        "vm",
        "vm.runInContext/runInNewContext",
        "eval",
        "runs arbitrary script text in a (weakly isolated) VM context",
        "node's vm module is not a security sandbox; never run untrusted code in it",
        "critical",
        ("vm.runInContext(", "vm.runInNewContext("),
        ("CWE-95",),
    ),
    # -- typescript/js: html_render -------------------------------------------
    _op(
        "typescript",
        "dom",
        "innerHTML/outerHTML/document.write",
        "html_render",
        "assigns raw HTML/attacker-controlled markup into the DOM",
        "use textContent, or sanitize with a vetted HTML sanitizer before "
        "assigning innerHTML",
        "high",
        ("innerHTML", "outerHTML", "document.write("),
        ("CWE-79",),
    ),
    _op(
        "typescript",
        "react",
        "dangerouslySetInnerHTML",
        "html_render",
        "React's explicit escape hatch for raw HTML injection",
        "sanitize with a vetted HTML sanitizer before use, or avoid raw HTML",
        "high",
        ("dangerouslySetInnerHTML",),
        ("CWE-79",),
    ),
    # -- typescript/js: client_storage ----------------------------------------
    _op(
        "typescript",
        "web-storage",
        "localStorage/sessionStorage",
        "client_storage",
        "persists data in browser storage readable by any script on the "
        "origin (XSS-adjacent exfil target)",
        "never store secrets/tokens in localStorage; use an httpOnly cookie",
        "medium",
        ("localStorage", "sessionStorage"),
        (),
    ),
    _op(
        "typescript",
        "indexeddb",
        "indexedDB",
        "client_storage",
        "persists structured data in browser storage",
        "never store secrets/tokens in indexedDB",
        "medium",
        ("indexedDB",),
        (),
    ),
    # -- typescript/js: net / fetch_url ---------------------------------------
    # RECLASSIFIED (reviewer diff-audit): the pre-T-0158 table put "fetch("
    # under typescript/net. This registry moves it to fetch_url instead --
    # same reasoning as python's urllib. above: fetch()'s actual danger is
    # SSRF (CWE-918), a more precise kind than generic net, not a dropped
    # needle.
    _op(
        "typescript",
        "fetch",
        "fetch()",
        "fetch_url",
        "fetches a URL that may be attacker-influenced (SSRF surface)",
        "validate/allowlist the target host before fetching",
        "medium",
        ("fetch(",),
        ("CWE-918",),
    ),
    _op(
        "typescript",
        "xhr",
        "XMLHttpRequest",
        "fetch_url",
        "issues an HTTP request that may target an attacker-influenced URL",
        "validate/allowlist the target host before requesting",
        "medium",
        ("XMLHttpRequest",),
        ("CWE-918",),
    ),
    _op(
        "typescript",
        "ws",
        "WebSocket",
        "net",
        "opens a persistent socket to an attacker-influenceable host",
        "validate/allowlist the target host before connecting",
        "medium",
        ("WebSocket(",),
        (),
    ),
    _op(
        "typescript",
        "http",
        "http.request/https.request",
        "net",
        "issues a raw HTTP(S) request, node's low-level client",
        "prefer a vetted HTTP client with a pinned timeout",
        "low",
        ('require("http")', "require('http')", "http.request(", "https.request("),
        (),
    ),
    _op(
        "typescript",
        "axios",
        "axios.get/post/...",
        "net",
        "third-party HTTP client issuing outbound requests",
        "pin a timeout; validate SSRF-sensitive URLs",
        "medium",
        ("axios.",),
        (),
    ),
    _op(
        "typescript",
        "net",
        "net.connect",
        "net",
        "opens a raw TCP socket",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("net.connect(",),
        (),
    ),
    # -- typescript/js: env / ffi / fs-write / install-hook -------------------
    _op(
        "typescript",
        "process",
        "process.env",
        "env",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("process.env",),
        (),
    ),
    _op(
        "typescript",
        "fs",
        "fs.writeFile/appendFile/unlink/rm",
        "fs-write",
        "mutates or removes local filesystem state",
        "validate the target path is inside an expected root before writing",
        "low",
        ("fs.writeFile", "fs.appendFile", "fs.unlink", "fs.rm("),
        ("CWE-22",),
    ),
    _op(
        "typescript",
        "fs",
        "fs.readFile/readFileSync",
        "fs-read",
        "reads local filesystem state",
        "validate the source path is inside an expected root before reading",
        "low",
        ("fs.readFile", "readFileSync("),
        (),
    ),
    _op(
        "typescript",
        "node-ffi",
        "ffi-napi/node-gyp/napi native bindings",
        "ffi",
        "loads and calls into native code via a node addon",
        "avoid loading native addons from untrusted or writable paths",
        "high",
        # T-0019 (graphite adoption): bare "napi" is deliberately NOT a plain
        # needle here -- it is also a substring of the ordinary English/API
        # word "openapi" ("o-p-e-n-[napi]"), which fired on openapi-typescript
        # codegen (api.generated.ts) with zero real node-ffi/ffi-napi usage.
        # "napi" is still detected, but only via the identifier-boundary
        # `_has_word_boundary_napi` special check in `frob.vet._capability`
        # (mirrors T-0151's `_has_bare_compile_call` precedent for the same
        # "needle is a substring of an unrelated word" class of bug).
        ("ffi-napi", "node-gyp"),
        (),
    ),
    # install-hook has no idiomatic JS/TS packaging-hook equivalent to
    # setuptools cmdclass; kept table-symmetric via CAPABILITY_MATRIX_EXCUSES.
    # -- rust: exec ------------------------------------------------------------
    _op(
        "rust",
        "std::process",
        "Command::new",
        "exec",
        "spawns an external process with the current process's privileges",
        "validate the program/args come from a trusted, fixed set",
        "high",
        ("Command::new(",),
        ("CWE-78",),
    ),
    # -- rust: ffi ---------------------------------------------------------
    _op(
        "rust",
        "std",
        'extern "C" (FFI declaration)',
        "ffi",
        "declares/calls into native code across the FFI boundary, opting out "
        "of Rust's memory safety",
        "keep the unsafe surface minimal and audited",
        "high",
        ('extern "C"',),
        (),
    ),
    _op(
        "rust",
        "libc",
        "libc:: native syscalls",
        "ffi",
        'direct libc FFI calls, same native-code boundary as extern "C"',
        "keep the unsafe surface minimal and audited",
        "high",
        ("libc::",),
        (),
    ),
    _op(
        "rust",
        "libloading",
        "libloading::Library::new",
        "ffi",
        "loads a shared library at runtime and calls into it dynamically",
        "avoid loading libraries from untrusted or writable paths",
        "critical",
        ("libloading::",),
        (),
    ),
    _op(
        "rust",
        "std::mem",
        "mem::transmute",
        "eval",
        "reinterprets a value's bits as an arbitrary other type, the sharpest "
        "escape hatch from Rust's type system",
        "prefer a safe conversion (TryFrom, as, or a checked cast helper)",
        "critical",
        ("mem::transmute",),
        (),
    ),
    # -- rust: net ---------------------------------------------------------
    _op(
        "rust",
        "std::net",
        "TcpStream/std::net::*",
        "net",
        "opens a raw network socket",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("TcpStream", "std::net::"),
        (),
    ),
    _op(
        "rust",
        "reqwest",
        "reqwest::Client/get/post",
        "net",
        "third-party HTTP client issuing outbound requests",
        "pin a timeout; validate SSRF-sensitive URLs",
        "medium",
        ("reqwest::",),
        (),
    ),
    _op(
        "rust",
        "hyper",
        "hyper::Client",
        "net",
        "third-party low-level HTTP client issuing outbound requests",
        "pin a timeout; validate SSRF-sensitive URLs",
        "medium",
        ("hyper::",),
        (),
    ),
    # -- rust: fs-write ------------------------------------------------------
    _op(
        "rust",
        "std::fs",
        "File::create/fs::write/fs::remove_file",
        "fs-write",
        "mutates or removes local filesystem state",
        "validate the target path is inside an expected root before writing",
        "low",
        ("File::create(", "fs::write(", "fs::remove_file("),
        ("CWE-22",),
    ),
    # -- rust: fs-read (T-0018, graphite adoption) --------------------------
    _op(
        "rust",
        "std::fs",
        "fs::read_to_string/fs::read",
        "fs-read",
        "reads local filesystem state",
        "validate the source path is inside an expected root before reading",
        "low",
        ("fs::read_to_string(", "fs::read("),
        (),
    ),
    # -- rust: env -----------------------------------------------------------
    _op(
        "rust",
        "std::env",
        "env::var/env::vars",
        "env",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("std::env::var(", "std::env::vars("),
        (),
    ),
    # -- kotlin: net (T-0170, Android node capability-scan column) -------------
    _op(
        "kotlin",
        "okhttp3",
        "OkHttpClient/Retrofit",
        "net",
        "the dominant Android HTTP client (and Retrofit, built on top of it) "
        "issuing outbound requests",
        "pin a timeout; validate SSRF-sensitive URLs; enable certificate pinning",
        "medium",
        ("OkHttpClient(", "okhttp3.", "Retrofit.Builder("),
        (),
    ),
    _op(
        "kotlin",
        "java.net",
        "HttpURLConnection",
        "net",
        "the JDK's built-in HTTP client, opening an outbound connection",
        "prefer a higher-level client with TLS verification (OkHttp)",
        "medium",
        ("HttpURLConnection",),
        (),
    ),
    # -- kotlin: exec ------------------------------------------------------
    _op(
        "kotlin",
        "java.lang",
        "Runtime.getRuntime().exec",
        "exec",
        "spawns an external process with the current process's privileges",
        "validate the program/args come from a trusted, fixed set",
        "high",
        ("Runtime.getRuntime().exec(",),
        ("CWE-78",),
    ),
    _op(
        "kotlin",
        "java.lang",
        "ProcessBuilder",
        "exec",
        "spawns an external process with the current process's privileges",
        "validate the program/args come from a trusted, fixed set",
        "high",
        ("ProcessBuilder(",),
        ("CWE-78",),
    ),
    # -- kotlin: client_storage ----------------------------------------------
    _op(
        "kotlin",
        "android.content",
        "SharedPreferences/getSharedPreferences",
        "client_storage",
        "reads/writes the Android app's on-device key-value store, a "
        "common landing spot for tokens/PII if left unencrypted",
        "prefer EncryptedSharedPreferences (Jetpack Security) for sensitive values",
        "low",
        ("SharedPreferences", "getSharedPreferences("),
        (),
    ),
    _op(
        "kotlin",
        "androidx.room",
        "RoomDatabase/@Database",
        "client_storage",
        "the dominant on-device SQLite ORM for Android; stored rows can "
        "carry sensitive data if unencrypted",
        "use SQLCipher-backed Room (net.zetetic:android-database-sqlcipher) "
        "for sensitive data",
        "low",
        ("RoomDatabase", "@Database("),
        (),
    ),
    # -- c/c++: exec -----------------------------------------------------------
    _op(
        "c-cpp",
        "libc",
        "system()",
        "exec",
        "runs a command through the shell with the current process's privileges",
        "use exec* with a fixed argv array, never a shell-interpreted string",
        "critical",
        ("system(",),
        ("CWE-78",),
    ),
    _op(
        "c-cpp",
        "libc",
        "popen()",
        "exec",
        "opens a shell pipe to/from a command",
        "use posix_spawn/exec* with a fixed argv array",
        "high",
        ("popen(",),
        ("CWE-78",),
    ),
    _op(
        "c-cpp",
        "libc",
        "exec* family (execl/execv/execve/...)",
        "exec",
        "replaces the process image, running attacker-influenceable input if "
        "the path/argv is untrusted",
        "validate the program path and argv come from a trusted, fixed set",
        "high",
        (
            "execl(",
            "execv(",
            "execve(",
            "execvp(",
            "execle(",
            "execvpe(",
            "posix_spawn(",
            "posix_spawnp(",
            "fexecve(",
        ),
        ("CWE-78",),
    ),
    # T-0400 audit finding #4: the exec table above was POSIX-only; a
    # Windows-targeted C/C++ dependency can launch a process through the
    # Win32 API entirely, evading every needle above.
    _op(
        "c-cpp",
        "windows.h",
        "CreateProcess()/ShellExecute()/WinExec()",
        "exec",
        "launches a process (optionally through the shell) via the Win32 API",
        "use CreateProcess with a fixed argv array and no shell interpretation",
        "critical",
        (
            "CreateProcessA(",
            "CreateProcessW(",
            "ShellExecuteA(",
            "ShellExecuteW(",
            "WinExec(",
        ),
        ("CWE-78",),
    ),
    # -- c/c++: fs-read (T-0018, graphite adoption) ----------------------------
    _op(
        "c-cpp",
        "libc",
        "fread()/fgets()",
        "fs-read",
        "reads local filesystem state",
        "validate the source path is inside an expected root before reading",
        "low",
        ("fread(", "fgets("),
        (),
    ),
    # T-0400 audit finding #4: `open()`/`read()`/`mmap()` are the actual
    # POSIX read syscalls; only the buffered stdio wrappers above were
    # patterned, so a dependency reading via raw fds was invisible.
    _op(
        "c-cpp",
        "libc",
        "open()/read()/mmap()",
        "fs-read",
        "reads local filesystem state via a raw file descriptor",
        "validate the source path is inside an expected root before reading",
        "low",
        ("open(", "read(", "mmap("),
        (),
    ),
    # -- c/c++: ffi (dynamic loading) ------------------------------------------
    _op(
        "c-cpp",
        "libdl",
        "dlopen()",
        "ffi",
        "loads a shared library at runtime and resolves symbols dynamically",
        "avoid loading libraries from untrusted or writable paths",
        "critical",
        ("dlopen(",),
        (),
    ),
    # -- c/c++: memory-unsafe string ops (fs-write-adjacent buffer surface) ---
    # Bucketed under fs-write (not a new memory-corruption kind): CWE-120's
    # own sink is a fixed-size BUFFER, the closest existing capability_kind
    # analog this registry has to "writes past an intended boundary" --
    # taxonomically loose (buffer != filesystem) but no dedicated
    # memory-corruption kind exists yet in CAPABILITY_KINDS, and inventing
    # one for a single c-cpp-only entry is deferred to a future ticket
    # rather than done ad hoc here.
    _op(
        "c-cpp",
        "libc",
        "strcpy/sprintf/gets family",
        "fs-write",
        "unbounded string copy/format into a fixed buffer, the classic "
        "stack-smashing primitive",
        "use strncpy/snprintf/fgets with an explicit bound",
        "critical",
        ("strcpy(", "sprintf(", "gets("),
        ("CWE-120",),
    ),
    # T-0400 audit finding #4: `fopen`/`fwrite`/`write`/`rename`/`unlink`/
    # `mkdir` are the ACTUAL fs-write surface (the strcpy-family entry above
    # is a memory-safety bucket, not a real file write) -- the audit's
    # repro was a dependency that opens+writes an arbitrary file via
    # fopen/fwrite and scanned as zero capabilities.
    _op(
        "c-cpp",
        "libc",
        "fopen()/fwrite()/write()/rename()/unlink()/mkdir()",
        "fs-write",
        "creates, overwrites, renames, deletes, or writes local filesystem state",
        "validate the destination path is inside an expected, writable root",
        "high",
        ("fopen(", "fwrite(", "write(", "rename(", "unlink(", "mkdir("),
        (),
    ),
    # -- c/c++: net -----------------------------------------------------------
    _op(
        "c-cpp",
        "sys/socket.h",
        "socket()/connect()/bind()",
        "net",
        "opens a raw network socket via the BSD sockets API",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("socket(", "connect(", "bind("),
        (),
    ),
    # T-0400 audit finding #4: send/recv/sendto/recvfrom/getaddrinfo were
    # entirely absent -- a dependency that connects via a helper but does
    # its actual I/O through these calls scanned as net-capability-free.
    _op(
        "c-cpp",
        "sys/socket.h",
        "send()/recv()/sendto()/recvfrom()/getaddrinfo()",
        "net",
        "sends/receives data or resolves a hostname over a network socket",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("send(", "recv(", "sendto(", "recvfrom(", "getaddrinfo("),
        (),
    ),
    # -- python: third-party priority survey (T-0181, T-0158 addendum 2 -----
    # remainder) -- pydantic/fastapi/cryptography/alembic/argon2-cffi are
    # deliberately NOT patterned here: surveyed against their actual API
    # surface and found to have no dangerous-operation idiom distinct from
    # what the generic entries above already cover. See docs/modules/vet.md
    # "Third-party library survey (T-0181)" for the full per-library
    # disposition table, pure libraries included.
    _op(
        "python",
        "numpy",
        "numpy.load(..., allow_pickle=True)",
        "deserialize",
        "loading a .npy/.npz file with allow_pickle=True lets the file's "
        "embedded pickle stream execute arbitrary code on load",
        "never set allow_pickle=True for untrusted files; the default (False) is safe",
        "critical",
        ("allow_pickle=True",),
        ("CWE-502",),
    ),
    _op(
        "python",
        "jinja2",
        "jinja2.Template()/Environment.from_string()",
        "eval",
        "rendering a template built from attacker-influenced text is "
        "server-side template injection: Jinja2 expressions can reach "
        "arbitrary Python via __class__ traversal",
        "never build a template from untrusted input; use a fixed template "
        "file with a safe, data-only context",
        "critical",
        ("jinja2.Template(", "Environment.from_string("),
        ("CWE-1336", "CWE-95"),
    ),
    _op(
        "python",
        "jinja2",
        "Environment(autoescape=False)",
        "html_render",
        "disables Jinja2's automatic HTML escaping, letting injected markup "
        "render unescaped",
        "use autoescape=True (or select_autoescape) for any HTML-producing environment",
        "high",
        ("autoescape=False",),
        ("CWE-79",),
    ),
    _op(
        "python",
        "python-dotenv",
        "dotenv.load_dotenv",
        "env",
        "loads environment variables from a .env file into the process environment",
        "keep .env out of version control and out of any untrusted-writable path",
        "low",
        ("load_dotenv(",),
        (),
    ),
    _op(
        "python",
        "uvicorn",
        "uvicorn.run",
        "net",
        "binds and serves an ASGI application on a network socket",
        "bind only to a trusted interface and pin host/port explicitly",
        "medium",
        ("uvicorn.run(",),
        (),
    ),
    _op(
        "python",
        "sqlalchemy",
        "sqlalchemy.text() with string-formatted SQL",
        "sql",
        "wrapping a string-formatted/f-string SQL fragment in text() "
        "re-opens the injection surface parameterized queries close",
        "use bound parameters (text(sql).bindparams(...)) or the query "
        "builder; never interpolate values into the string",
        "high",
        ("sqlalchemy.text(",),
        ("CWE-89",),
    ),
    _op(
        "python",
        "asyncpg",
        "asyncpg.connect",
        "net",
        "opens an async PostgreSQL network connection using supplied credentials/host",
        "validate the connection target and load credentials from a vetted "
        "secret store",
        "medium",
        ("asyncpg.connect(",),
        (),
    ),
    _op(
        "python",
        "boto3",
        "boto3.client()/boto3.resource()",
        "net",
        "creates an AWS SDK client/resource using ambient or supplied cloud "
        "credentials -- an outbound net + cloud-credential surface",
        "scope credentials via IAM least privilege; never accept an "
        "attacker-controlled service name/endpoint",
        "medium",
        ("boto3.client(", "boto3.resource("),
        (),
    ),
    _op(
        "python",
        "stripe",
        "stripe.api_key / stripe.Charge.create",
        "net",
        "issues authenticated payment-processing API calls carrying a live secret key",
        "load stripe.api_key from a vetted secret store; never accept "
        "attacker-controlled amounts/params unvalidated",
        "medium",
        ("stripe.api_key",),
        (),
    ),
    _op(
        "python",
        "anthropic",
        "anthropic.Anthropic()/client.messages.create",
        "net",
        "issues authenticated outbound API calls to the Anthropic API "
        "carrying an API key",
        "load the API key from a vetted secret store; validate/bound any "
        "user-influenced prompt content",
        "low",
        ("anthropic.Anthropic(",),
        (),
    ),
    _op(
        "python",
        "aiosmtpd",
        "aiosmtpd.controller.Controller",
        "net",
        "runs an SMTP server accepting inbound network connections",
        "bind only to a trusted interface; validate/sanitize all inbound "
        "message handling",
        "medium",
        ("aiosmtpd.controller.Controller(",),
        (),
    ),
    _op(
        "python",
        "playwright",
        "sync_playwright()/async_playwright() browser launch",
        "exec",
        "launches a full browser as a subprocess",
        "never launch a browser against untrusted automation scripts "
        "without sandboxing",
        "medium",
        ("sync_playwright(", "async_playwright("),
        (),
    ),
    _op(
        "python",
        "playwright",
        "page.evaluate()",
        "eval",
        "executes arbitrary JavaScript inside the automated page context",
        "never pass untrusted input as script; use fixed, parameterized "
        "functions with page.evaluate",
        "high",
        ("page.evaluate(",),
        ("CWE-95",),
    ),
    _op(
        "python",
        "Pillow",
        "PIL.ImageMath.eval",
        "eval",
        "evaluates a string expression against image data, an eval-adjacent primitive",
        "never build the ImageMath expression from untrusted input",
        "high",
        ("ImageMath.eval(",),
        ("CWE-95",),
    ),
    # -- typescript/js: third-party priority survey (T-0181) -----------------
    # react/react-dom, vite/vitest, openapi-typescript, and the eslint
    # tooling family are deliberately NOT patterned here: surveyed and found
    # to have no dangerous-operation idiom distinct from what the generic
    # entries above already cover (react's dangerouslySetInnerHTML is
    # already patterned). See docs/modules/vet.md "Third-party library
    # survey (T-0181)".
    _op(
        "typescript",
        "playwright",
        "chromium.launch()/firefox.launch()/webkit.launch()",
        "exec",
        "launches a full browser as a subprocess",
        "never launch a browser against untrusted automation scripts "
        "without sandboxing",
        "medium",
        ("chromium.launch(", "firefox.launch(", "webkit.launch("),
        (),
    ),
    _op(
        "typescript",
        "playwright",
        "page.evaluate()",
        "eval",
        "executes arbitrary JavaScript inside the automated page context",
        "never pass untrusted input as script; use fixed, parameterized "
        "functions with page.evaluate",
        "high",
        ("page.evaluate(",),
        ("CWE-95",),
    ),
    # -- rust: third-party priority survey (T-0181) --------------------------
    # serde/serde_json, tracing, and thiserror/crossbeam are deliberately
    # NOT patterned here: type-directed (de)serialization, structured
    # logging, and pure library/derive-macro utilities respectively, with no
    # dangerous-operation idiom. libloading is already patterned above
    # (T-0158). See docs/modules/vet.md "Third-party library survey
    # (T-0181)".
    _op(
        "rust",
        "pyo3",
        "Python::with_gil / pyo3::prelude",
        "ffi",
        "embeds/calls into the Python interpreter from Rust across the FFI boundary",
        "keep the embedded-Python surface minimal and audited; never eval "
        "attacker-controlled Python strings through it",
        "high",
        ("pyo3::", "Python::with_gil("),
        (),
    ),
    _op(
        "rust",
        "wasm-bindgen",
        "#[wasm_bindgen] / wasm_bindgen::",
        "ffi",
        "exposes Rust functions to (and calls into) JavaScript across the "
        "wasm/JS FFI boundary",
        "validate/sanitize every value crossing the wasm/JS boundary",
        "medium",
        ("wasm_bindgen::", "#[wasm_bindgen]"),
        (),
    ),
)


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0158
#: every (kind, language) cell with NO `_DangerousOperation` entry above
#: gets a SPECIFIC excuse naming the missing idiom -- the blanket C/C++
#: "honestly-empty" exemption is retired (T-0158). An unexcused empty cell
#: is a `capability_matrix()` gate failure.
CAPABILITY_MATRIX_EXCUSES: tuple[_MatrixExcuse, ...] = (
    _MatrixExcuse(
        capability_kind="eval",
        language="c-cpp",
        reason="no idiomatic C/C++ 'evaluate a string as code' primitive in "
        "the standard library; dlopen (ffi) is the closest native-code-"
        "loading analog and is already patterned separately",
    ),
    _MatrixExcuse(
        capability_kind="env",
        language="c-cpp",
        reason="getenv()/setenv() reads are pervasive, unprefixed C identifiers "
        "(`getenv(` collides with countless unrelated tokens under a plain-"
        "substring scanner) -- tracked as a real gap, not silently dropped; "
        "see docs/modules/vet.md 'Honest limits'",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="c-cpp",
        reason="no C/C++ packaging-install-hook idiom analogous to setuptools "
        "cmdclass; native builds hook via Makefile/CMake, outside this "
        "scanner's per-source-file text model",
    ),
    _MatrixExcuse(
        capability_kind="html_render",
        language="c-cpp",
        reason="no C/C++ standard-library DOM/HTML-rendering concept; "
        "browser-only capability",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="c-cpp",
        reason="no single dominant C/C++ DB-API string-interpolation idiom "
        "(libpq/sqlite3 C APIs use bound parameters as the common path); "
        "tracked as a gap for the next C SQL-client survey, not claimed covered",
    ),
    _MatrixExcuse(
        capability_kind="fetch_url",
        language="c-cpp",
        reason="no single dominant C/C++ URL-fetch idiom in the standard "
        "library (libcurl is third-party); covered via the closed-world "
        "vetted-library path for libcurl-linked dependencies, not a hand "
        "pattern here",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="c-cpp",
        reason="no C/C++ standard-library object-deserialization primitive "
        "analogous to pickle/marshal; unsafe deserialization in C/C++ is a "
        "buffer-parsing bug, already covered by the strcpy/sprintf/gets "
        "fs-write-bucketed entries",
    ),
    _MatrixExcuse(
        capability_kind="client_storage",
        language="c-cpp",
        reason="no C/C++ standard-library browser-storage concept; browser-"
        "only capability",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="typescript",
        reason="no idiomatic npm packaging-install-hook literal analogous to "
        "setuptools cmdclass; npm lifecycle scripts (preinstall/postinstall) "
        "are declared in package.json data, not source text this scanner "
        "reads -- tracked as a real gap, not silently dropped",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="typescript",
        reason="no single dominant raw-SQL-string-interpolation idiom "
        "shared across node DB clients (pg/mysql2/knex each differ); ORM "
        "query-builder usage is the common path and is not itself dangerous "
        "-- tracked as a gap for a per-client survey",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="typescript",
        reason="JSON.parse is the dominant deserialization primitive and is "
        "not itself unsafe (no code execution on parse, unlike pickle); "
        "prototype-pollution-adjacent merge utilities are a distinct, "
        "narrower gap tracked separately, not this kind",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="rust",
        reason="idiomatic Rust DB clients (sqlx/diesel) are compile-time "
        "parameterized by design; no dominant raw-string-interpolation "
        "idiom exists to pattern",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="rust",
        reason="serde is the dominant (de)serialization crate and is type-"
        "directed, not string-eval-based; unsafe deserialization in Rust is "
        "a `mem::transmute`/unsafe-FFI concern, already patterned under eval/"
        "ffi",
    ),
    _MatrixExcuse(
        capability_kind="html_render",
        language="rust",
        reason="no single dominant Rust templating-crate raw-HTML-injection "
        "idiom surveyed yet (askama/maud/tera each differ); tracked as a "
        "follow-up per-crate survey, not claimed covered",
    ),
    _MatrixExcuse(
        capability_kind="client_storage",
        language="rust",
        reason="no Rust standard-library browser-storage concept; browser-"
        "only capability (wasm-bindgen web-sys bindings are a follow-up "
        "survey item, not covered here)",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="rust",
        reason="no Rust packaging-install-hook idiom analogous to setuptools "
        "cmdclass; cargo build.rs is itself already the exec-capability "
        "surface (patterned separately as build.rs -> Command::new)",
    ),
    _MatrixExcuse(
        capability_kind="client_storage",
        language="python",
        reason="no Python standard-library browser-storage concept; browser-"
        "only capability",
    ),
    _MatrixExcuse(
        capability_kind="fetch_url",
        language="rust",
        reason="reqwest::/hyper:: are already patterned under net (fetching a "
        "URL IS the SSRF-relevant surface for those crates); no separate "
        "fetch_url-specific idiom distinct from the net entries exists in "
        "Rust's ecosystem to pattern independently",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="python",
        reason="`fs` is `_effects.py::_KIND_MAP`'s tier-2-normalized alias "
        "of the scanner's `fs-write` kind (net/fs-write/exec are "
        "normalized to net/fs/exec for `may` declarations); every actual "
        "detection pattern lives under `fs-write`, this is the same "
        "cell under its normalized name, not a separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="typescript",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="rust",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="c-cpp",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface",
    ),
    # -- kotlin (T-0170): every cell NOT patterned above, excused honestly --
    _MatrixExcuse(
        capability_kind="eval",
        language="kotlin",
        reason="no idiomatic string-eval/dynamic-code-execution primitive in "
        "common Android/Kotlin use; the closest analog (reflection-based "
        "class loading) is a distinct, narrower ffi-adjacent gap tracked "
        "separately, not surveyed as a dominant idiom here",
    ),
    _MatrixExcuse(
        capability_kind="fs-write",
        language="kotlin",
        reason="Kotlin's filesystem access goes through the same java.io/"
        "java.nio surface as any JVM language, with no single dominant "
        "write idiom distinct enough to needle cheaply without a wider "
        "per-API survey; tracked as a follow-up, not guessed at here",
    ),
    _MatrixExcuse(
        capability_kind="fs",
        language="kotlin",
        reason="see the python/fs excuse above -- same tier-2 alias, no "
        "separate detection surface (and fs-write itself is excused for "
        "kotlin, see above)",
    ),
    _MatrixExcuse(
        capability_kind="fs-read",
        language="kotlin",
        reason="same java.io/java.nio survey gap as fs-write above -- no "
        "single dominant read idiom surveyed yet",
    ),
    _MatrixExcuse(
        capability_kind="env",
        language="kotlin",
        reason="System.getenv() is the obvious JVM idiom but was not part of "
        "T-0170's per-cell survey list (net/exec/client_storage only); "
        "tracked as a follow-up rather than guessed at here",
    ),
    _MatrixExcuse(
        capability_kind="ffi",
        language="kotlin",
        reason="JNI (System.loadLibrary/native methods) is the JVM ffi "
        "idiom but was not part of T-0170's per-cell survey list; tracked "
        "as a follow-up rather than guessed at here",
    ),
    _MatrixExcuse(
        capability_kind="install-hook",
        language="kotlin",
        reason="no Kotlin/Android packaging-install-hook idiom analogous to "
        "setuptools cmdclass; Gradle build-script tasks are the closest "
        "analog and are already trusted-author build tooling, not a "
        "runtime dependency capability",
    ),
    _MatrixExcuse(
        capability_kind="html_render",
        language="kotlin",
        reason="Android has no dominant raw-HTML-injection idiom analogous "
        "to a web templating engine; WebView.loadData/loadDataWithBaseURL "
        "is the closest analog and is a distinct, narrower gap not yet "
        "surveyed",
    ),
    _MatrixExcuse(
        capability_kind="sql",
        language="kotlin",
        reason="Room (already patterned under client_storage) is the "
        "dominant Android SQL surface and is compile-time/annotation "
        "checked by design; raw SQLiteDatabase.rawQuery string "
        "interpolation is a distinct, narrower gap not yet surveyed",
    ),
    _MatrixExcuse(
        capability_kind="fetch_url",
        language="kotlin",
        reason="OkHttp/HttpURLConnection are already patterned under net "
        "(fetching a URL IS the SSRF-relevant surface for those clients); "
        "no separate fetch_url-specific idiom distinct from the net "
        "entries exists to pattern independently",
    ),
    _MatrixExcuse(
        capability_kind="deserialize",
        language="kotlin",
        reason="Gson/Moshi/kotlinx.serialization are the dominant "
        "(de)serialization libraries and are type-directed, not "
        "string-eval-based; a per-library survey is deferred as a "
        "follow-up rather than guessed at here",
    ),
    # T-0244: `embedded_code` is emitted structurally (a tree-sitter STRING
    # node's size + HTML/JS-signal heuristic in `frob.vet._capability`),
    # never from a per-language `DANGEROUS_OPERATIONS` needle -- every
    # language cell is excused the same way, symmetrically, rather than
    # patterned per language.
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="python",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="typescript",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="rust",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="c-cpp",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
    _MatrixExcuse(
        capability_kind="embedded_code",
        language="kotlin",
        reason="detected structurally by _capability._embedded_code_regions "
        "(STRING-node size + HTML/JS signal heuristic), not a per-language "
        "needle pattern -- see T-0244",
    ),
)


# T-0524: frob:doc removed -- capability_matrix (public, below) returns
# this type and already carries the same docs/modules/vet.md#public-api
# anchor (COV007).
class _MatrixCell(BaseModel):
    """One (capability_kind, language) matrix cell's verdict: `patterned`
    (has >=1 `_DangerousOperation`), `excused` (has a `_MatrixExcuse`), or
    neither -- the last case is a gate failure (T-0158)."""

    model_config = ConfigDict(frozen=True)

    capability_kind: str
    language: str
    patterned: bool
    excused: bool
    operation_count: int
    excuse_reason: str | None = None


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0158
def capability_matrix() -> tuple[_MatrixCell, ...]:
    """The full (kind x language) matrix: every cell is `patterned`,
    `excused`, or -- if neither -- a gate failure the caller must surface.
    Deterministic order: kind-major, then `LANGUAGES` order."""
    excuse_by_key = {
        (e.capability_kind, e.language): e for e in CAPABILITY_MATRIX_EXCUSES
    }
    counts: dict[tuple[str, str], int] = {}
    for entry in DANGEROUS_OPERATIONS:
        key = (entry.capability_kind, entry.language)
        counts[key] = counts.get(key, 0) + 1

    cells: list[_MatrixCell] = []
    for kind in CAPABILITY_KINDS:
        for language in LANGUAGES:
            key = (kind, language)
            operation_count = counts.get(key, 0)
            excuse = excuse_by_key.get(key)
            cells.append(
                _MatrixCell(
                    capability_kind=kind,
                    language=language,
                    patterned=operation_count > 0,
                    excused=excuse is not None,
                    operation_count=operation_count,
                    excuse_reason=excuse.reason if excuse else None,
                )
            )
    return tuple(cells)


# T-0524: frob:doc removed -- calls capability_matrix (public), which
# already carries the same docs/modules/vet.md#public-api anchor (COV007).
# frob:ticket T-0158
# frob:ticket T-0565
# frob:tests tests/test_capability_registry.py::TestMatrixExhaustiveness.test_no_unexcused_empty_cells  # noqa: E501
def _unexcused_empty_cells() -> tuple[_MatrixCell, ...]:
    """Every matrix cell with zero patterns and zero excuse -- the T-0158
    gate failure condition. Empty tuple = the exhaustiveness claim holds."""
    return tuple(c for c in capability_matrix() if not c.patterned and not c.excused)


# frob:doc docs/modules/vet.md#public-api
# frob:waive COV007 reason="a standalone drift-lock helper with no public wrapper -- \
# called directly by its own tests (T-0524), not through any other public entrypoint \
# in this module, so the private symbol genuinely is the documented contract here"
# frob:ticket T-0158
# frob:ticket T-0565
# frob:tests tests/test_capability_registry.py::TestValidateRegistryKinds.test_known_kinds_pass  # noqa: E501
def _validate_registry_kinds(external_kinds: frozenset[str]) -> tuple[str, ...]:
    """Drift-lock (extends T-0150): every kind `external_kinds` names (e.g.
    every `WeaknessEntry.capability_kind`, every `may` atom kind observed
    in strata design files) must be a member of `CAPABILITY_KINDS`. Returns
    the offending kinds -- empty tuple means clean."""
    known = frozenset(CAPABILITY_KINDS)
    offenders = tuple(sorted(external_kinds - known))
    if offenders:
        _log.error(
            "capability registry: %d kind(s) used but not registered: %s",
            len(offenders),
            offenders,
        )
    return offenders


# frob:doc docs/modules/vet.md#public-api
#: Python stdlib modules explicitly known to have NO effectful (process/fs/
#: net/env/dynamic-code) surface -- listed so "we curated exhaustively" is
#: checkable rather than "we sampled a few and moved on" (T-0158 addendum
#: 2). Not exhaustive over the ENTIRE stdlib (hundreds of modules); this is
#: the common/likely-imported subset a dependency's source is plausible to
#: use, curated alongside the effectful modules above. Extending this list
#: is always safe (adding a no-capability entry never masks a real finding
#: -- the module's actual text is still scanned by `DANGEROUS_OPERATIONS`
#: needles regardless of this list; this is documentation of intent, not a
#: skip-list).
NO_CAPABILITY_MODULES: tuple[str, ...] = (
    "collections",
    "itertools",
    "functools",
    "dataclasses",
    "typing",
    "enum",
    "abc",
    "math",
    "statistics",
    "decimal",
    "fractions",
    "random",
    "string",
    "re",
    "textwrap",
    "unicodedata",
    "difflib",
    "json",
    "csv",
    "datetime",
    "calendar",
    "zoneinfo",
    "copy",
    "pprint",
    "reprlib",
    "numbers",
    "array",
    "heapq",
    "bisect",
    "weakref",
    "types",
    "operator",
    "contextlib",
    "graphlib",
    "warnings",
    "traceback",
    "unittest",
    "doctest",
    "logging",
)


# frob:ticket T-0665
class _OpaqueConstruct(BaseModel):
    """One `docs/design/capability-evasion-taxonomy.md` "runtime-opaque"
    row that IS syntactically visible at the source-text level (T-0665,
    coordinator-signed category 1: "evasion-indicative dynamic lookup"):
    a call form whose determining argument is a NON-LITERAL expression --
    `eval`/`exec` (no literal split possible, always opaque), `getattr`/
    `setattr`/`__import__`/`importlib.import_module` with a non-literal
    name argument, `dlsym` with a non-literal symbol argument, JS/TS
    dynamic `import(expr)` with a non-literal specifier, and every
    reflection-API entry (`Class.forName`, `Method.invoke`,
    `KCallable.call`) which is opaque unconditionally -- reflection
    resolves through runtime metadata even when the class/method NAME
    literal is visible in source, unlike a plain import/attribute name.
    `literal_arg_index` is `None` for constructs that are always opaque
    regardless of any literal argument (`eval`, reflection); otherwise the
    0-based argument position `frob.vet._capability`'s heuristic checks for
    a literal (a string/byte-string literal there downgrades the site to
    the ordinary resolver path, per the coordinator's T-0665 sign-off:
    "literal-key lookups that resolve statically belong to the ordinary
    resolver path, not this gate")."""

    model_config = ConfigDict(frozen=True)

    language: str
    construct_name: str
    needle: str
    literal_arg_index: int | None
    rationale: str
    taxonomy_row: str


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0665
# frob:ticket T-1047
# frob:waive AFFECT001 reason="T-1047 extended this tuple with 15 more \
# entries (same shape as the existing ones); docs/modules/vet.md is outside \
# T-1047's declared scope (src/frob/vet/**, src/frob/gates/_opaque.py, \
# docs/design/registry/evasion.yaml, tests/test_vet.py) -- matches T-0665's \
# own precedent for the identical situation on this same constant"
# frob:enforces EVA-PY-R01
# frob:enforces EVA-PY-R02
# frob:enforces EVA-PY-R03
# frob:enforces EVA-PY-R04
# frob:enforces EVA-PY-R05
# frob:enforces EVA-PY-R06
# frob:enforces EVA-PY-R07
# frob:enforces EVA-PY-R08
# frob:enforces EVA-PY-R09
# frob:enforces EVA-TSJS-R01
# frob:enforces EVA-TSJS-R02
# frob:enforces EVA-TSJS-R03
# frob:enforces EVA-TSJS-R04
# frob:enforces EVA-TSJS-R05
# frob:enforces EVA-TSJS-R06
# frob:enforces EVA-TSJS-R07
# frob:enforces EVA-TSJS-R08
# frob:enforces EVA-TSJS-R09
# frob:enforces EVA-RS-R01
# frob:enforces EVA-RS-R02
# frob:enforces EVA-RS-R03
# frob:enforces EVA-RS-R04
# frob:enforces EVA-RS-R05
# frob:enforces EVA-RS-R06
# frob:enforces EVA-C-R01
# frob:enforces EVA-C-R02
# frob:enforces EVA-C-R03
# frob:enforces EVA-C-R04
# frob:enforces EVA-C-R05
# frob:enforces EVA-CPP-R01
# frob:enforces EVA-CPP-R02
# frob:enforces EVA-CPP-R03
# frob:enforces EVA-CPP-R04
# frob:enforces EVA-CPP-R05
# frob:enforces EVA-KT-R01
# frob:enforces EVA-KT-R02
# frob:enforces EVA-KT-R03
# frob:enforces EVA-KT-R04
# frob:enforces EVA-KT-R05
RUNTIME_OPAQUE_CONSTRUCTS: tuple[_OpaqueConstruct, ...] = (
    _OpaqueConstruct(
        language="python",
        construct_name="eval",
        needle="eval(",
        literal_arg_index=None,
        rationale="arbitrary source text evaluated at runtime; no literal "
        "argument can make this statically resolvable",
        taxonomy_row="python:runtime:eval",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="exec",
        needle="exec(",
        literal_arg_index=None,
        rationale="arbitrary source text executed at runtime; no literal "
        "argument can make this statically resolvable",
        taxonomy_row="python:runtime:exec",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="getattr",
        needle="getattr(",
        literal_arg_index=1,
        rationale="a non-literal attribute name is resolved by runtime "
        'lookup; a literal name (`getattr(subprocess, "run")`) is '
        "equivalent to the plain attribute access the ordinary resolver "
        "already handles",
        taxonomy_row="python:runtime:getattr-dynamic-name",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="setattr",
        needle="setattr(",
        literal_arg_index=1,
        rationale="a non-literal attribute name means the mutated site is "
        "not visible to any static binding table -- mirrors getattr's split",
        taxonomy_row="python:runtime:setattr-monkeypatch",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="__import__",
        needle="__import__(",
        literal_arg_index=0,
        rationale="a non-literal module-name argument is resolved by "
        "runtime string computation",
        taxonomy_row="python:runtime:dunder-import-computed-name",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="importlib.import_module",
        needle="importlib.import_module(",
        literal_arg_index=0,
        rationale="same computed-module-name opacity as __import__, "
        "importlib's documented equivalent entry point",
        taxonomy_row="python:runtime:importlib-import-module",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="eval",
        needle="eval(",
        literal_arg_index=None,
        rationale="arbitrary source text evaluated at runtime",
        taxonomy_row="typescript:runtime:eval",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Function constructor",
        needle="new Function(",
        literal_arg_index=None,
        rationale="arbitrary source text compiled into a new function at "
        "runtime, ECMA-262 20.2.1",
        taxonomy_row="typescript:runtime:function-constructor",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="dynamic import()",
        needle="import(",
        literal_arg_index=0,
        rationale="a non-literal specifier is resolved by runtime module "
        'loading; `import("literal/path")` is statically enumerable and '
        "belongs to the ordinary resolver path",
        taxonomy_row="typescript:runtime:dynamic-import-call",
    ),
    _OpaqueConstruct(
        language="c-cpp",
        construct_name="dlsym",
        needle="dlsym(",
        literal_arg_index=1,
        rationale="POSIX dynamic symbol lookup; a non-literal symbol-name "
        "argument is resolved by runtime string computation. A literal "
        'symbol name (`dlsym(h, "run_cmd")`) is still resolved by the '
        "dynamic LINKER at load time (not this scanner), but the source "
        "text at least names the target for a human/tool to grep -- the "
        "coordinator's category-1 split treats this as the ordinary-"
        "resolver boundary the same way it does for getattr/dlopen's "
        "python-side analog",
        taxonomy_row="c:runtime:dlopen-dlsym",
    ),
    _OpaqueConstruct(
        language="rust",
        construct_name="libloading symbol lookup",
        needle=".get(",
        literal_arg_index=None,
        rationale="a `libloading::Library::get` dynamic symbol lookup -- "
        "unconditionally opaque per the coordinator's T-0665 sign-off (no "
        "literal/non-literal split given for this row, unlike C's dlsym); "
        "this needle is deliberately broad (bare `.get(`) since the "
        "receiver type cannot be confirmed without full type inference -- "
        "a disclosed over-approximation gated to files that also import "
        "`libloading` (see `_rust_file_uses_libloading` in "
        "frob.vet._capability), not a claim of call-site precision",
        taxonomy_row="rust:runtime:libloading-dlsym",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="Class.forName",
        needle="Class.forName(",
        literal_arg_index=None,
        rationale="reflection resolves through JVM runtime metadata even "
        "when the class-name literal is visible in source -- unlike a "
        "plain import/attribute name, no literal argument makes the "
        "SUBSEQUENT .getMethod()/.invoke() chain statically resolvable",
        taxonomy_row="kotlin:runtime:class-forname-invoke",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="KCallable.call",
        needle=".call(",
        literal_arg_index=None,
        rationale="a `KCallable`/`KFunction` obtained dynamically (e.g. via "
        "`::class.members`) and invoked through `.call` -- the bound "
        "target is runtime metadata, unconditionally opaque; this needle "
        "is deliberately broad (`.call(` alone) since the receiver type "
        "cannot be confirmed without full type inference -- a disclosed "
        "over-approximation, not a claim of precision",
        taxonomy_row="kotlin:runtime:kcallable-call",
    ),
    # T-1047: closing the ~25 taxonomy runtime-opaque rows T-0666 found with
    # no `RUNTIME_OPAQUE_CONSTRUCTS`/`OPAQUE_SOURCE_INVISIBLE` entry. Each
    # needle below is the same deliberately-broad, disclosed-over-
    # approximation style as the libloading/`.call(` entries above -- a
    # fixed substring that names the evasion-indicative construct without
    # claiming call-site type precision; false positives are waivable
    # (category-1 doctrine, T-0665).
    _OpaqueConstruct(
        language="python",
        construct_name="functools.partial",
        needle="functools.partial(",
        literal_arg_index=None,
        rationale="a `functools.partial`/decorator indirection whose bound "
        "target is computed at runtime is not visible to the ordinary "
        "static resolver; unconditionally opaque since the target "
        "expression's literalness cannot be determined without full "
        "dataflow",
        taxonomy_row="python:runtime:functools-partial-dynamic-target",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="__getattr__ interception",
        needle="def __getattr__(",
        literal_arg_index=None,
        rationale="a class defining `__getattr__`/`__getattribute__` can "
        "route ANY attribute access to an arbitrary runtime-resolved "
        "target, making every subsequent access through an instance of "
        "that class opaque to the ordinary resolver",
        taxonomy_row="python:runtime:dunder-getattr-class-interception",
    ),
    _OpaqueConstruct(
        language="python",
        construct_name="sys.modules replacement",
        needle="sys.modules[",
        literal_arg_index=None,
        rationale="a direct `sys.modules[name] = fake_module` write "
        "replaces what every SUBSEQUENT `import name` in the process "
        "resolves to, at runtime -- the module identity a static import "
        "resolver assumes is a lie",
        taxonomy_row="python:runtime:sys-modules-replacement",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="globalThis[name]",
        needle="globalThis[",
        literal_arg_index=None,
        rationale="a computed-key access through `globalThis` reaches any "
        "global binding by a runtime-computed name, unconditionally "
        "opaque to a static resolver",
        taxonomy_row="typescript:runtime:globalthis-bracket",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Reflect.get",
        needle="Reflect.get(",
        literal_arg_index=None,
        rationale="`Reflect.get` resolves its target property through "
        "runtime reflection metadata, same opacity class as Python's "
        "`getattr` with a non-literal name",
        taxonomy_row="typescript:runtime:reflect-get-dynamic-target",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Reflect.apply",
        needle="Reflect.apply(",
        literal_arg_index=None,
        rationale="`Reflect.apply` invokes a runtime-resolved callable "
        "target through reflection metadata, unconditionally opaque",
        taxonomy_row="typescript:runtime:reflect-apply-dynamic-target",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="Proxy interception",
        needle="new Proxy(",
        literal_arg_index=None,
        rationale="a `Proxy` `get`/`apply` trap can route any property "
        "access or call through the target object to an arbitrary "
        "runtime-computed handler, opaque to the ordinary resolver",
        taxonomy_row="typescript:runtime:proxy-interception",
    ),
    _OpaqueConstruct(
        language="typescript",
        construct_name="monkeypatch module namespace",
        needle="require.cache[",
        literal_arg_index=None,
        rationale="mutating a loaded module's exports via `require.cache` "
        "rewrites what every OTHER importer of that module resolves to, "
        "at runtime -- the same module-identity opacity as Python's "
        "`sys.modules` replacement row",
        taxonomy_row="typescript:runtime:monkeypatch-module-namespace",
    ),
    _OpaqueConstruct(
        language="c-cpp",
        construct_name="reinterpret_cast to function pointer",
        needle="reinterpret_cast<",
        literal_arg_index=None,
        rationale="a `reinterpret_cast` from an integer/opaque handle to a "
        "function-pointer type synthesizes a call target with no "
        "compile-time relationship to any named function -- deliberately "
        "broad needle (any `reinterpret_cast<`) since confirming the "
        "target TYPE is a function pointer needs full type inference; a "
        "disclosed over-approximation, not a claim of precision",
        taxonomy_row="cpp:runtime:reinterpret-cast-function-pointer",
    ),
    _OpaqueConstruct(
        language="c-cpp",
        construct_name="RTTI-driven dispatch",
        needle="typeid(",
        literal_arg_index=None,
        rationale="`typeid`/`dynamic_cast`-driven branching selects "
        "behavior based on runtime type information rather than a "
        "statically-enumerable override set, unlike ordinary bounded "
        "virtual dispatch",
        taxonomy_row="cpp:runtime:rtti-driven-dispatch",
    ),
    _OpaqueConstruct(
        language="rust",
        construct_name="function pointer in container",
        needle="Vec<fn(",
        literal_arg_index=None,
        rationale="a function pointer read back out of a runtime-indexed "
        "container (`Vec<fn(...)>` read via a non-constant index) has no "
        "static binding to a single named function at the read site; "
        "deliberately broad needle (any `Vec<fn(` type annotation), a "
        "disclosed over-approximation matching the libloading needle's "
        "own precedent",
        taxonomy_row="rust:runtime:function-pointer-in-container",
    ),
    _OpaqueConstruct(
        language="rust",
        construct_name="Box<dyn Fn> runtime-selected",
        needle="Box<dyn Fn",
        literal_arg_index=None,
        rationale="a `Box<dyn Fn>` built from a runtime-selected source "
        "(one of several closures chosen by a runtime condition) erases "
        "which concrete closure is bound at the call site",
        taxonomy_row="rust:runtime:boxed-dyn-fn-runtime-selected",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="function value in container",
        needle="]!!(",
        literal_arg_index=None,
        rationale="a function value read out of a runtime-indexed "
        "container and immediately non-null-asserted and invoked "
        "(`handlers[key]!!(x)`) has no static binding to a single named "
        "function at the call site; deliberately broad needle (any "
        "`]!!(` non-null-assert-then-call), a disclosed over-"
        "approximation",
        taxonomy_row="kotlin:runtime:function-value-in-container",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="delegated property by",
        needle="by lazy {",
        literal_arg_index=None,
        rationale="a delegated property (`by lazy { ... }`) resolves its "
        "value through the delegate's runtime-evaluated initializer block "
        "rather than a statically-visible binding -- deliberately broad "
        "needle, a disclosed over-approximation (most `by lazy` blocks "
        "hold ordinary data, not callables; waivable per category-1 "
        "doctrine when the delegate is confirmed non-callable)",
        taxonomy_row="kotlin:runtime:delegated-property-by",
    ),
    _OpaqueConstruct(
        language="kotlin",
        construct_name="dynamic classloading",
        needle="URLClassLoader(",
        literal_arg_index=None,
        rationale="`URLClassLoader`/reflection-based classloading resolves "
        "a class (and therefore any method invoked on it) from a runtime-"
        "computed name or byte source, unconditionally opaque",
        taxonomy_row="kotlin:runtime:dynamic-classloading",
    ),
)

# T-0665: source-invisible taxonomy rows (coordinator sign-off category 3)
# -- constructs no source-text or per-file AST scan can see because the
# resolution happens at a layer this scanner never observes (the dynamic
# linker/loader, a JIT'd vtable, or an out-of-process plugin loader).
# Each entry is a REG011-compliant "none -- <explanation>" disposition
# naming why source-level analysis cannot see it and what layer could,
# cross-registered in docs/design/registry/check-coverage.yaml so the REG
# gates keep these accountable forever rather than silently forgotten.
# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0665
# frob:ticket T-1047
# frob:waive AFFECT001 reason="T-1047 extended this tuple with 2 more \
# entries (same shape as the existing ones); docs/modules/vet.md is outside \
# T-1047's declared scope (src/frob/vet/**, src/frob/gates/_opaque.py, \
# docs/design/registry/evasion.yaml, tests/test_vet.py) -- matches T-0665's \
# own precedent for the identical situation on this same constant"
OPAQUE_SOURCE_INVISIBLE: tuple[_MatrixExcuse, ...] = (
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="c-cpp",
        reason="none -- weak-symbol interposition (GNU/ELF __attribute__"
        "((weak))) and LD_PRELOAD-class symbol override are resolved by "
        "the DYNAMIC LINKER at process-load time, never visible to a "
        "per-source-file text/AST scan; the source at every call site is "
        "textually identical whether or not it gets interposed. Only a "
        "deploy/host-level obligation (frob.strata's host-isolation model, "
        "docs/strata/host.md) can observe the actual linked artifact set, "
        "not this file-level scanner.",
    ),
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="rust",
        reason="none -- a runtime vtable patch (unsafe raw-pointer rewrite "
        "of a trait object's vtable slot) is process-memory manipulation "
        "with no distinguishing source-text shape from ordinary unsafe "
        "pointer arithmetic; only runtime instrumentation (not a static "
        "source scan) could observe it.",
    ),
    # T-1047: two more rust source-invisible constructs, distinct from the
    # vtable-patch entry above -- each excused for its own reason, not a
    # shared blanket rust exemption (REG011 accountability per entry).
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="rust",
        reason="none -- an `extern` block FFI symbol is bound by the "
        "DYNAMIC LINKER at process-load time (same layer as C's weak-"
        "symbol interposition above), never visible to a per-source-file "
        'text/AST scan; the `extern "C" { fn ... }` declaration names '
        "the symbol, but which concrete implementation actually answers "
        "the call is a link-time/load-time fact this scanner cannot see.",
    ),
    _MatrixExcuse(
        capability_kind="opaque-capability-indirection",
        language="rust",
        reason="none -- a procedural/derive macro (`#[derive(...)]`, "
        "attribute or function-like proc-macros) synthesizes its expanded "
        "call sites inside a separate compiler-plugin crate that runs at "
        "macro-expansion time; the expansion is not present in the "
        "annotated source text at all, so no source-level scan of this "
        "file can see what call, if any, the macro emits. Mirrors the "
        "ordinary resolver's own honest non-detection of `macro_rules!` "
        "expansion (`test_macro_rules_expansion_emitting_fixed_call_not_"
        "detected`) -- proc-macros are the same opacity class one layer "
        "further from source visibility.",
    ),
)


# frob:ticket T-1051
class _OpaqueStructuralConstruct(BaseModel):
    """One T-1051 "needle-architecture-blocked" taxonomy row that the
    fixed-needle-plus-literal-arg shape `_OpaqueConstruct` implements
    cannot express without an unacceptable false-positive rate: a
    SHAPE (subscript-then-call, or cast-then-call) rather than a fixed
    substring. `kind` selects which structural scanner in
    `frob.vet._capability` (`_structural_opaque_findings`) applies:
    `"subscript_call"` for `container[non_literal_key](...)` (python/
    typescript container-dynamic-key and computed-member rows, C/C++
    array-index function-pointer dispatch), `"explicit_fnptr_cast_call"`
    for `((RET(*)(ARGS))expr)(...)` (C/C++ integer-cast-to-function-
    pointer), and `"named_type_cast_call"` for `((TypeName)expr)(...)`
    (C/C++ void*-backcast-to-function-pointer through a typedef'd
    function-pointer type). Same disclosed-over-approximation posture as
    `_OpaqueConstruct`'s needles -- these scanners cannot confirm the
    subscript index or cast target TYPE without full type inference, so
    they fire on the STRUCTURAL SHAPE alone; false positives are
    waivable (category-1 doctrine, T-0665), consistent with the
    `libloading`/`.call(` entries' own precedent."""

    model_config = ConfigDict(frozen=True)

    language: str
    construct_name: str
    kind: str
    rationale: str
    taxonomy_row: str


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-1051
# frob:waive AFFECT001 reason="T-1051 adds this new tuple (same shape as \
# RUNTIME_OPAQUE_CONSTRUCTS above); docs/modules/vet.md is outside T-1051's \
# declared scope (src/frob/vet/**, src/frob/gates/_opaque.py, \
# docs/design/registry/evasion.yaml, tests/test_vet.py) -- matches T-0665's \
# own precedent for the identical situation on RUNTIME_OPAQUE_CONSTRUCTS"
RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS: tuple[_OpaqueStructuralConstruct, ...] = (
    _OpaqueStructuralConstruct(
        language="python",
        construct_name="container dynamic-key call",
        kind="subscript_call",
        rationale="a callable read out of a container (dict/list) through a "
        "NON-LITERAL subscript key/index and immediately called -- the "
        "bound target depends on the container's runtime contents at the "
        "computed key, invisible to the ordinary resolver's bounded "
        "single-literal-binding dataflow. Covers both the taxonomy's "
        "'callable in a container, dynamic key' row and its 'computed "
        "member access, non-constant key' row -- identical source shape, "
        "`container[expr](...)`",
        taxonomy_row="python:runtime:container-dynamic-key-call",
    ),
    _OpaqueStructuralConstruct(
        language="typescript",
        construct_name="container dynamic-key call",
        kind="subscript_call",
        rationale="same shape as the python row: `handlers[key](x)`/"
        "`cp[key](x)` reads a callable out of an object/array through a "
        "runtime-computed key and calls it immediately. Covers both the "
        "'callable in container, dynamic key' row and the 'computed "
        "member access, non-constant key' row",
        taxonomy_row="typescript:runtime:container-dynamic-key-call",
    ),
    _OpaqueStructuralConstruct(
        language="c-cpp",
        construct_name="array-index function-pointer dispatch",
        kind="subscript_call",
        rationale="a function-pointer TABLE indexed by a non-constant "
        "expression and immediately called (`tbl[user_selected_index]"
        '("sh")`) -- the ordinary resolver already proves this stays '
        "unresolved as a static binding (`test_array_fn_ptr_nonconstant_"
        "index_not_detected`); this is the fail-closed obligation's own "
        "sibling catch",
        taxonomy_row="c:runtime:array-index-fnptr-dispatch",
    ),
    _OpaqueStructuralConstruct(
        language="c-cpp",
        construct_name="integer-cast to function pointer",
        kind="explicit_fnptr_cast_call",
        rationale="an explicit function-pointer TYPE cast "
        "(`((void(*)(const char*))addr)(...)`) of an arbitrary expression "
        "(commonly an integer/opaque handle) immediately called -- the "
        "cast type is visible in source, but the VALUE being cast is not "
        "provably a valid function address by any static check",
        taxonomy_row="c:runtime:integer-cast-to-function-pointer",
    ),
    _OpaqueStructuralConstruct(
        language="c-cpp",
        construct_name="void* back-cast to function pointer",
        kind="named_type_cast_call",
        rationale="a `void*` value cast through a named (often typedef'd) "
        "type and immediately called (`((Handler)p)(...)`) -- the cast "
        "TARGET TYPE cannot be confirmed as a real function-pointer "
        "typedef without full type inference, so this fires on the "
        "structural shape alone (a parenthesized single-identifier cast "
        "immediately called), a disclosed over-approximation",
        taxonomy_row="c:runtime:void-star-backcast-to-function-pointer",
    ),
)


__all__ = [
    "CAPABILITY_KINDS",
    "CAPABILITY_MATRIX_EXCUSES",
    "DANGEROUS_OPERATIONS",
    "LANGUAGES",
    "NO_CAPABILITY_MODULES",
    "OPAQUE_SOURCE_INVISIBLE",
    "RUNTIME_OPAQUE_CONSTRUCTS",
    "RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS",
    "_DangerousOperation",
    "_MatrixCell",
    "_MatrixExcuse",
    "_OpaqueConstruct",
    "_OpaqueStructuralConstruct",
    "capability_matrix",
    "_unexcused_empty_cells",
    "_validate_registry_kinds",
]
