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
    # T-2464: split out of the coarse "requests." needle above -- a
    # module-level mutating-verb call (POST/PUT/DELETE/PATCH) is a real,
    # DIFFERENT signal from a read-only GET/HEAD/OPTIONS call, which the
    # coarse needle alone cannot distinguish. Additive: "requests." above
    # is UNCHANGED and still fires on every requests usage including
    # these calls -- this is a strictly more precise SECOND observation,
    # never a narrowing of the first. Covers only the module-level
    # convenience functions (`requests.post(url)`); a `session.post(url)`
    # call on a `requests.Session()` instance is NOT covered (the bare
    # `.post(` method name is indistinguishable from any other object's
    # `.post` method at the flat-needle level without false-positive risk
    # -- disclosed, not silently dropped, T-2464 Done report).
    _op(
        "python",
        "requests",
        "requests.post/put/delete/patch (module-level mutating verb)",
        "net-mutate",
        "issues a state-changing HTTP request (POST/PUT/DELETE/PATCH), "
        "distinct from a read-only GET -- may create/modify/delete a "
        "remote resource",
        "pin a timeout and verify=True; validate SSRF-sensitive URLs; "
        "treat as a mutating operation for authorization/audit purposes",
        "medium",
        ("requests.post(", "requests.put(", "requests.delete(", "requests.patch("),
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
    # T-2464: same split as requests. above, module-level convenience
    # functions only (`httpx.post(url)`) -- `httpx.Client().post(url)`
    # instance-method calls are NOT covered, same disclosed gap.
    _op(
        "python",
        "httpx",
        "httpx.post/put/delete/patch (module-level mutating verb)",
        "net-mutate",
        "issues a state-changing HTTP request (POST/PUT/DELETE/PATCH), "
        "distinct from a read-only GET -- may create/modify/delete a "
        "remote resource",
        "pin a timeout and verify=True; validate SSRF-sensitive URLs; "
        "treat as a mutating operation for authorization/audit purposes",
        "medium",
        ("httpx.post(", "httpx.put(", "httpx.delete(", "httpx.patch("),
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
    # T-2457: "open(" removed from this entry's needles. The bare
    # substring matched ANY open() call regardless of mode -- a read-mode
    # `open(path, "rb")` satisfied this fs-write rule on its own, which is
    # exactly the false-positive this ticket fixes (it forced seven false
    # `fs.write` declarations into design/frob.strata for modules that
    # provably only read). `open(`/`.open(` calls are now classified by
    # `frob.vet._capability_core._has_write_mode_open_call`, a mode-aware
    # token-level parse of the call's arguments wired in via
    # `_SPECIAL_CHECKS`/`_operation_entry_matches` (this entry's own empty
    # `needles` tuple is what routes it through that fallback -- see
    # `_operation_entry_matches`'s T-2457 comment). `.write(` stays a
    # plain needle: any `.write(...)` call is unambiguously a write
    # regardless of what it's called on.
    _op(
        "python",
        "builtins",
        "open() (write/append mode)",
        "fs-write",
        "writes/overwrites local filesystem state",
        "validate the target path is inside an expected root before writing",
        "low",
        (".write(",),
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
    # T-2479: split out of the coarse "boto3.client(/resource(" needle above
    # -- boto3's mutating operation names are PER-SERVICE (S3's put_object/
    # delete_object vs DynamoDB's put_item/delete_item vs IAM's
    # create_user/delete_user) and only ever called on the object a
    # `.client("service")`/`.resource("service")` call returns, with no
    # library-name prefix at the call site itself -- a flat needle cannot
    # distinguish these from a read (get_object/get_item/list_users)
    # without a binding-aware resolver. `frob.vet._capability_python`'s
    # `_resolve_py_boto3_client_call` (T-2479) resolves
    # `x = boto3.client("s3")` to the synthetic identity
    # `boto3.client(s3)`, so `x.put_object(...)` resolves all the way to
    # `boto3.client(s3).put_object` and matches the needles below.
    # Additive: the coarse "boto3.client(" / "boto3.resource(" needle
    # above is UNCHANGED and still fires on every boto3 usage including
    # these calls -- this is a strictly more precise SECOND observation.
    # Scope disclosed, matching T-2464's own precedent: this covers three
    # HIGH-VALUE services (S3, DynamoDB, IAM) with a representative, not
    # exhaustive, mutating-verb list for each -- a full per-service survey
    # across boto3's ~350 services is out of scope here (filed as a
    # follow-up, see T-2479's Done report).
    _op(
        "python",
        "boto3",
        'boto3 S3 mutating verb (put/delete/create on client/resource("s3"))',
        "net-mutate",
        "issues a state-changing AWS S3 API call (put/delete/create an "
        "object, bucket, or ACL/policy) -- may destroy or expose data",
        "scope credentials via IAM least privilege; treat as a mutating "
        "operation for authorization/audit purposes; never accept "
        "attacker-controlled bucket/key names unvalidated",
        "high",
        tuple(
            f"boto3.{factory}(s3).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "put_object",
                "delete_object",
                "delete_objects",
                "create_bucket",
                "delete_bucket",
                "put_object_acl",
                "put_bucket_acl",
                "put_bucket_policy",
                "delete_bucket_policy",
                "copy_object",
                "upload_file",
                "upload_fileobj",
                "restore_object",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        "boto3 DynamoDB mutating verb (put/delete/update/create on "
        'client/resource("dynamodb"))',
        "net-mutate",
        "issues a state-changing AWS DynamoDB API call (put/delete/update "
        "an item or table) -- may destroy or corrupt data",
        "scope credentials via IAM least privilege; treat as a mutating "
        "operation for authorization/audit purposes; validate item "
        "keys/attributes before writing",
        "high",
        tuple(
            f"boto3.{factory}(dynamodb).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "put_item",
                "delete_item",
                "update_item",
                "create_table",
                "delete_table",
                "update_table",
                "batch_write_item",
                "transact_write_items",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        'boto3 IAM mutating verb (create/delete/attach/put on client/resource("iam"))',
        "net-mutate",
        "issues a state-changing AWS IAM API call (create/delete a "
        "user/role/policy or attach/detach a policy) -- a cloud-privilege "
        "escalation surface, the single most consequential class this "
        "needle table models",
        "scope credentials via IAM least privilege; require a human "
        "review/approval gate before any IAM-mutating call path executes",
        "critical",
        tuple(
            f"boto3.{factory}(iam).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "create_user",
                "delete_user",
                "update_user",
                "create_role",
                "delete_role",
                "put_role_policy",
                "delete_role_policy",
                "attach_role_policy",
                "detach_role_policy",
                "create_policy",
                "delete_policy",
                "attach_user_policy",
                "detach_user_policy",
                "create_access_key",
                "delete_access_key",
            )
        ),
        (),
    ),
    # T-2500: exhaustive per-service boto3 survey, next tier after S3/
    # DynamoDB/IAM -- same _op(...) shape, same binding-aware resolver
    # (frob.vet._capability_python._resolve_py_boto3_client_call, T-2479),
    # no resolver changes needed, only new per-service needle tables.
    # Scope disclosed: this covers 7 more HIGH-VALUE services (EC2, RDS,
    # Lambda, SNS, SQS, Secrets Manager, KMS) with representative, not
    # exhaustive, mutating-verb lists -- boto3 has ~350 services total;
    # the remainder is out of scope here (see T-2500's own Done report
    # for what remains and why an exhaustive survey was not attempted in
    # one pass).
    _op(
        "python",
        "boto3",
        'boto3 EC2 mutating verb (run/terminate/modify on client/resource("ec2"))',
        "net-mutate",
        "issues a state-changing AWS EC2 API call (launch/terminate an "
        "instance, modify a security group, attach/detach a volume) -- "
        "can create billable resources or open network exposure",
        "scope credentials via IAM least privilege; treat as a mutating "
        "operation for authorization/audit purposes; never accept "
        "attacker-controlled instance/security-group parameters unvalidated",
        "high",
        tuple(
            f"boto3.{factory}(ec2).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "run_instances",
                "terminate_instances",
                "stop_instances",
                "reboot_instances",
                "create_security_group",
                "delete_security_group",
                "authorize_security_group_ingress",
                "authorize_security_group_egress",
                "revoke_security_group_ingress",
                "revoke_security_group_egress",
                "create_volume",
                "delete_volume",
                "attach_volume",
                "detach_volume",
                "create_snapshot",
                "delete_snapshot",
                "create_key_pair",
                "delete_key_pair",
                "modify_instance_attribute",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        'boto3 RDS mutating verb (create/delete/modify on client/resource("rds"))',
        "net-mutate",
        "issues a state-changing AWS RDS API call (create/delete a "
        "database instance, take/delete a snapshot) -- may destroy "
        "production data or create billable resources",
        "scope credentials via IAM least privilege; treat as a mutating "
        "operation for authorization/audit purposes; require a human "
        "review/approval gate before any delete_db_instance-shaped call",
        "critical",
        tuple(
            f"boto3.{factory}(rds).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "create_db_instance",
                "delete_db_instance",
                "modify_db_instance",
                "reboot_db_instance",
                "create_db_snapshot",
                "delete_db_snapshot",
                "restore_db_instance_from_db_snapshot",
                "create_db_cluster",
                "delete_db_cluster",
                "modify_db_cluster",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        "boto3 Lambda mutating verb (create/delete/update-code on "
        'client/resource("lambda"))',
        "net-mutate",
        "issues a state-changing AWS Lambda API call (create/delete a "
        "function, update its code or configuration) -- a code-execution "
        "surface: a mutated function's code runs with its own IAM role "
        "on the next invocation",
        "scope credentials via IAM least privilege; treat as a mutating "
        "operation for authorization/audit purposes; require code review "
        "before any update_function_code-shaped call reaches production",
        "critical",
        tuple(
            f"boto3.{factory}(lambda).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "create_function",
                "delete_function",
                "update_function_code",
                "update_function_configuration",
                "add_permission",
                "remove_permission",
                "publish_version",
                "create_alias",
                "delete_alias",
                "update_alias",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        'boto3 SNS mutating verb (publish/create/delete on client/resource("sns"))',
        "net-mutate",
        "issues a state-changing AWS SNS API call (publish a message, "
        "create/delete a topic or subscription) -- lower severity than "
        "IAM/Lambda but still an outbound-notification and topology "
        "mutation surface",
        "scope credentials via IAM least privilege; validate message "
        "content/topic ARNs before publishing",
        "medium",
        tuple(
            f"boto3.{factory}(sns).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "publish",
                "create_topic",
                "delete_topic",
                "subscribe",
                "unsubscribe",
                "set_topic_attributes",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        'boto3 SQS mutating verb (send/create/delete on client/resource("sqs"))',
        "net-mutate",
        "issues a state-changing AWS SQS API call (send/delete a "
        "message, create/delete/purge a queue) -- lower severity than "
        "IAM/Lambda but still a queue-topology and message-injection "
        "surface",
        "scope credentials via IAM least privilege; validate message "
        "content before sending; never purge a queue on attacker-"
        "controlled input",
        "medium",
        tuple(
            f"boto3.{factory}(sqs).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "send_message",
                "send_message_batch",
                "delete_message",
                "delete_message_batch",
                "create_queue",
                "delete_queue",
                "purge_queue",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        "boto3 Secrets Manager mutating verb (create/delete/put/rotate on "
        'client/resource("secretsmanager"))',
        "net-mutate",
        "issues a state-changing AWS Secrets Manager API call "
        "(create/delete a secret, update its value, rotate it) -- "
        "credential-adjacent, IAM-like severity: a mutated secret can "
        "break every consumer or leak a new value",
        "scope credentials via IAM least privilege; require a human "
        "review/approval gate before any delete_secret or put_secret_"
        "value-shaped call",
        "critical",
        tuple(
            f"boto3.{factory}(secretsmanager).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "create_secret",
                "delete_secret",
                "put_secret_value",
                "update_secret",
                "rotate_secret",
                "restore_secret",
            )
        ),
        (),
    ),
    _op(
        "python",
        "boto3",
        "boto3 KMS mutating verb (create/delete/disable/schedule on "
        'client/resource("kms"))',
        "net-mutate",
        "issues a state-changing AWS KMS API call (create/schedule "
        "deletion of a key, disable a key, re-encrypt data under a "
        "different key) -- credential-adjacent, IAM-like severity: a "
        "scheduled key deletion is irreversibly destructive to anything "
        "encrypted under that key",
        "scope credentials via IAM least privilege; require a human "
        "review/approval gate before any schedule_key_deletion-shaped "
        "call -- this is the single most destructive verb in this table",
        "critical",
        tuple(
            f"boto3.{factory}(kms).{verb}("
            for factory in ("client", "resource")
            for verb in (
                "create_key",
                "schedule_key_deletion",
                "cancel_key_deletion",
                "disable_key",
                "enable_key",
                "put_key_policy",
                "create_grant",
                "revoke_grant",
            )
        ),
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
