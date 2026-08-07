"""`_OTHER_OPERATIONS`: the typescript/rust/kotlin/c-cpp slice of
`DANGEROUS_OPERATIONS` (T-1420 split, python's own slice sibling lives in
`_dangerous_ops_python.py`) -- these four languages share one file since
none is individually close to the 800-line threshold on its own."""

from __future__ import annotations

from frob.vet._capability_registry._schemas import _DangerousOperation, _op

_OTHER_OPERATIONS: tuple[_DangerousOperation, ...] = (
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
        "opens a raw TCP socket",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("net.connect(",),
        (),
    ),
    # T-0771: listen-side counterpart of the raw `net`/`http` client
    # entries above -- node's own low-level server-bind idioms.
    _op(
        "typescript",
        "net",
        "net.createServer/http.createServer",
        "net-listen",
        "binds and accepts inbound network connections",
        "bind only to a trusted interface and pin host/port explicitly",
        "medium",
        ("net.createServer(", "http.createServer(", "https.createServer("),
        (),
    ),
    # -- typescript/js: env / ffi / fs-write / install-hook -------------------
    _op(
        "typescript",
        "process",
        "process.env",
        "env-read",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("process.env",),
        (),
    ),
    # T-0771: write-side counterpart of process.env read above -- assigning
    # into process.env mutates the process's own environment for any child
    # process it later spawns.
    _op(
        "typescript",
        "process",
        "process.env.X = ...",
        "env-write",
        "mutates process environment variables, inherited by any child "
        "process spawned afterward",
        "scope environment mutation through a config loader with an explicit allowlist",
        "low",
        ("process.env.",),
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
        "net-connect",
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
        "net-connect",
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
        "net-connect",
        "third-party low-level HTTP client issuing outbound requests",
        "pin a timeout; validate SSRF-sensitive URLs",
        "medium",
        ("hyper::",),
        (),
    ),
    # T-0771: listen-side counterpart of TcpStream/reqwest/hyper above.
    _op(
        "rust",
        "std::net",
        "TcpListener::bind",
        "net-listen",
        "binds a socket to a local address and accepts inbound connections",
        "bind only to a trusted interface",
        "medium",
        ("TcpListener",),
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
        "env-read",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("std::env::var(", "std::env::vars("),
        (),
    ),
    # T-0771: write-side counterpart of env::var/env::vars above.
    _op(
        "rust",
        "std::env",
        "env::set_var/env::remove_var",
        "env-write",
        "mutates process environment variables, inherited by any child "
        "process spawned afterward",
        "scope environment mutation through a config loader with an explicit allowlist",
        "low",
        ("env::set_var(", "env::remove_var("),
        (),
    ),
    # -- kotlin: net (T-0170, Android node capability-scan column) -------------
    _op(
        "kotlin",
        "okhttp3",
        "OkHttpClient/Retrofit",
        "net-connect",
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
        "net-connect",
        "the JDK's built-in HTTP client, opening an outbound connection",
        "prefer a higher-level client with TLS verification (OkHttp)",
        "medium",
        ("HttpURLConnection",),
        (),
    ),
    # T-0771: listen-side counterpart of okhttp3/HttpURLConnection above --
    # the JDK's own server-socket bind primitive.
    _op(
        "kotlin",
        "java.net",
        "ServerSocket",
        "net-listen",
        "binds a socket to a local address and accepts inbound connections",
        "bind only to a trusted interface",
        "medium",
        ("ServerSocket(",),
        (),
    ),
    # T-0771: kotlin/JVM env read/write -- System.getenv is the dominant
    # JDK idiom; the JVM has no supported process-environment MUTATION API
    # (System.getenv() returns an unmodifiable view; setting an env var for
    # a child process instead goes through ProcessBuilder.environment(),
    # which mutates the CHILD's environment map, not the calling process's
    # own -- so kotlin/env-write is excused below (CAPABILITY_MATRIX_
    # EXCUSES), not patterned with a misleading needle).
    _op(
        "kotlin",
        "java.lang",
        "System.getenv",
        "env-read",
        "reads process environment variables, which may carry secrets",
        "scope secret access through a config loader with an explicit allowlist",
        "low",
        ("System.getenv(",),
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
        "socket()/connect()",
        "net-connect",
        "opens a raw network socket and connects out via the BSD sockets API",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("socket(", "connect("),
        (),
    ),
    # T-0771: bind()/listen() is the listen-side counterpart of the BSD
    # sockets API, split out of the old combined socket()/connect()/bind()
    # entry so net's connect/listen mode split has a real needle
    # distinction to normalize against (mirrors the asyncio split above).
    _op(
        "c-cpp",
        "sys/socket.h",
        "bind()/listen()",
        "net-listen",
        "binds a socket to a local address and accepts inbound connections "
        "via the BSD sockets API",
        "bind only to a trusted interface",
        "medium",
        ("bind(", "listen("),
        (),
    ),
    # T-0400 audit finding #4: send/recv/sendto/recvfrom/getaddrinfo were
    # entirely absent -- a dependency that connects via a helper but does
    # its actual I/O through these calls scanned as net-capability-free.
    # Classified net-connect (not a separate mode): these operate on an
    # already-established or already-bound socket and carry no listen/
    # accept semantics of their own.
    _op(
        "c-cpp",
        "sys/socket.h",
        "send()/recv()/sendto()/recvfrom()/getaddrinfo()",
        "net-connect",
        "sends/receives data or resolves a hostname over a network socket",
        "prefer a higher-level client with TLS verification",
        "medium",
        ("send(", "recv(", "sendto(", "recvfrom(", "getaddrinfo("),
        (),
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
