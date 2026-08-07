"""`_PYTHON_OPERATIONS`: the python-language slice of `DANGEROUS_OPERATIONS`
(T-1420 split -- the single-language table earns its own file since python
is this registry's largest single-language slice by a wide margin)."""

from __future__ import annotations

from frob.vet._capability_registry._schemas import _DangerousOperation, _op

_PYTHON_OPERATIONS: tuple[_DangerousOperation, ...] = (
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "asyncio.open_connection",
        "net-connect",
        "opens an async network socket as a client",
        "prefer a higher-level client with TLS verification enabled",
        "medium",
        ("asyncio.open_connection(",),
        (),
    ),
    # T-0771: asyncio.start_server is the listen-side counterpart, split
    # out of the combined open_connection/start_server entry above so the
    # connect/listen mode split (frob.vet._capability_modes.FAMILY_MODES
    # "net") has a real per-needle distinction to normalize against.
    _op(
        "python",
        "asyncio",
        "asyncio.start_server",
        "net-listen",
        "binds and accepts inbound async network connections",
        "bind only to a trusted interface and pin host/port explicitly",
        "medium",
        ("asyncio.start_server(",),
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
        "env-read",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("os.environ", "os.getenv("),
        (),
    ),
    # T-0771: write-side counterpart of os.environ/os.getenv above --
    # os.putenv and an os.environ[...] assignment mutate the process's own
    # environment for any child process spawned afterward.
    _op(
        "python",
        "os",
        "os.environ[...] = / os.putenv",
        "env-write",
        "mutates process environment variables, inherited by any child "
        "process spawned afterward",
        "scope environment mutation through a config loader with an explicit allowlist",
        "low",
        ("os.putenv(", "os.environ["),
        (),
    ),
    # T-1439: reclassified from bare "env" -- neither of these two entries
    # reads or writes an environment variable; they are process-lifecycle/
    # signal-handling operations that only ever shared the "env" string by
    # a pre-existing kind-naming mismatch (T-0771's Done report flagged it
    # unfixed). "process-control" is the accurate kind; "install-hook" was
    # considered and rejected -- that kind is specifically packaging-
    # lifecycle code (setuptools cmdclass, npm postinstall), a different
    # semantic surface from a running process exiting or handling a signal.
    _op(
        "python",
        "sys",
        "sys.exit / os._exit",
        "process-control",
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
        "process-control",
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
        "env-write",
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
        "net-listen",
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "net-listen",
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
)
