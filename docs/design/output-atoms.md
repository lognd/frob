# Output atoms: every way a program writes, per language

Status: draft
Owner: grimble
Decisions: none
Audience: contributor

Provenance: research for ticket ~JXNJRTQ (owner request 2026-10-26),
the data source for the logging rule ~JKKJPTT ("all output goes through
a logging crate"). The atoms were enumerated from each language's
standard library surface (module and type indexes of the Rust `std`,
`libc` and `log`/`tracing` ecosystems, the Python library reference,
Node.js and WHATWG console docs, the .NET BCL and Unity scripting API,
the Java SE API, the Zig std, the POSIX/ISO C library and the Bash
reference manual), not guessed. Nothing here changes code; the rule reads
the TOML blocks below.

## 1. What an output atom is

An output atom is the smallest named symbol or syntactic form through
which a running program causes bytes or events to leave the process.
The logging rule treats an atom as a violation when a call (or macro
use, redirect, or FFI call) resolves to one of the symbols below and the
call site is outside the configured logging module.

Channels (`ch`), the destinations the rule reasons about:

| Channel | Meaning |
|---|---|
| `stdout` | the process standard output stream or fd 1 |
| `stderr` | the process standard error stream or fd 2 |
| `stream` | a writer whose destination is a parameter (file object, writer); only an output when the argument resolves to a std stream |
| `file` | a file opened or written by path |
| `fd` | a raw file descriptor or handle write, or a path that names a std stream (`/dev/stdout`, `/proc/self/fd/1`) |
| `syslog` | syslog, journald, the Windows event log, Android log |
| `debugger` | a debugger or IDE channel (`OutputDebugString`, `Debug.WriteLine`, the V8 inspector console) |
| `ffi` | output reached through a foreign call (libc `printf`, `write`) |
| `shell` | output by spawning a process whose stdio is inherited |
| `implicit` | output the runtime emits itself (panic message, uncaught exception trace, warnings); the atom is the API that triggers or redirects it |

Forms (`form`): `fn`, `macro`, `method`, `attr` (a std handle object
such as `sys.stdout`), `builtin`, `type` (a handle or sink constructor),
`cmd` (shell command or builtin), `redirect` (shell syntax), `ffi`.

## 2. Machine-readable data

Two kinds of fenced block carry the data. The rule (and
`gob-dev gen`) parse every fence whose info string is exactly
`toml output-languages` or `toml output-atoms`; prose, headings and
other fences are ignored, so adding an atom is one line and no code
change.

`output-languages` holds `[[language]]` rows:

| Key | Meaning |
|---|---|
| `id` | the `gob_languages::Language::name()` value, or a planned id (`java`, `zig`, `bash`, `c`) |
| `status` | `supported` (grammar in the workspace today) or `planned` (language-expansion epic) |
| `grammar` | the tree-sitter grammar crate that must parse the file |
| `resolution` | the symbolic resolution classes (section 3) the language needs; each atom's `via` is a subset |
| `replacement` | the sanctioned logging facade named in the finding message |

`output-atoms` holds one `language` key and an `atoms` array of inline
tables with: `id` (unique, `<lang>.<name>`), `ch`, `sym` (fully
qualified symbol path as the language writes it; `*` stands for any
path segment or receiver, `{1,2}` for an fd or stream argument filter),
`form`, `via` (the resolution classes that can hide this atom), `why`
(the reason it counts), `use` (the sanctioned replacement at the call
site). An optional `when` narrows the match to an argument condition
(for example only fd 1 or 2) and `sev = "advisory"` marks implicit or
low-signal atoms; the rule loads them but does not report them (see
section "Implementation status"). An optional `mode_arg` (0-based index
of the mode or flags argument, also read from a `mode=`/`flags=` keyword)
makes the atom fire only when that argument is a string literal naming a
writing mode (`w`, `a`, `x` or `+`), so a read-only `open(path)` is clean.

Detection is symbolic, never a text needle: the rule parses with the
named grammar, builds a per-file scope (imports, assignments, local
shadowing) and resolves each call target to a symbol path before looking
it up in `sym`. A local named `print`, a string or a comment never
matches.

## 3. Resolution classes

| Class | What the resolver must follow | Example |
|---|---|---|
| `import-alias` | `import a as b`, `use a as b`, `using B = A` | `import sys as s; s.stdout.write(x)` |
| `from-import` | name imported from a module, optionally renamed | `from sys import stdout as o` |
| `glob-import` | wildcard or `using static` | `use std::io::*;`, `using static System.Console;` |
| `assign-alias` | a variable bound to the symbol, then called | `p = print; p(x)`, `const log = console.log` |
| `attr-chain` | dotted member access resolved through the module graph | `os.path` style, `System.Console.Out` |
| `builtins-module` | the builtin namespace reachable as a module | `import builtins; builtins.print` |
| `dynamic-getattr` | string-keyed lookup of a known module member | `getattr(sys, "stdout")`, `process["stdout"]` |
| `reexport` | a wrapper module that re-exports or re-wraps the symbol | `from .util import say` where `say = print` |
| `destructure` | members pulled out by pattern | `const { log } = console` |
| `bind-call` | `fn.bind`, `functools.partial`, closures that capture the symbol | `console.log.bind(console)` |
| `macro-path` | macro invoked by absolute path or imported by name | `std::println!`, `use std::eprintln as e;` |
| `macro-wrap` | user `macro_rules!` or `#define` that expands to an atom | `macro_rules! say` |
| `global-object` | the global object spellings | `globalThis.console`, `window.console`, `self.console` |
| `require` | CommonJS and dynamic import forms | `require("node:fs").writeSync` |
| `handle-flow` | a std handle stored in a value then written elsewhere | `let mut o = io::stdout(); o.write_all(..)` |
| `path-literal` | a string constant that names a std stream path | `"/dev/stdout"`, `"/proc/self/fd/2"` |
| `fd-literal` | integer constant 1 or 2 flowing to a write | `os.write(1, b"x")` |
| `redirect-target` | shell redirects and `exec` fd rewiring | `echo x >&2`, `exec >log` |
| `extern-decl` | a foreign symbol declared by the program | `extern "C" { fn puts }`, `[DllImport]`, `ctypes.CDLL` |

Dynamic forms that cannot be resolved statically (computed attribute
names, `eval`) are reported as an `unresolved-dynamic` note, never
silently accepted.

For JavaScript and TypeScript the resolver follows `const` string and
integer bindings, nested and computed-literal destructuring, parameter
defaults, `with (console)` blocks, `require` and `createRequire`
aliases, `Reflect.get` with a literal key and `Reflect.apply`. It
reports as unresolved: a computed member name or `with` target it
cannot resolve, a non-literal `import()`/`require()` specifier, `eval`,
`Function`, `vm` runners, `setTimeout` with a code string, property
descriptor reflection over an output object, and `fs.writeSync` to an
fd that is not a known integer.

For C# the resolver reads `global::` qualified names as absolute paths,
follows `typeof(T).GetMethod("M")` and `Type.GetType("T")` (also through
a local variable) to the symbol `T.M`, and resolves base lists
symbolically (`using` aliases, namespaces and `global::`) into a
project-wide class hierarchy, so `print` inherited from
`UnityEngine.MonoBehaviour` is found through any chain of project
classes, across files, unless the class declares its own `print`.
`[DllImport]` and `[LibraryImport]` externs bind the managed method name
(or its `EntryPoint`) to `DllImport.<lib>.<entry>`, which the
`cs.pinvoke` row matches. It reports as unresolved: a reflective lookup
with a computed member name or type that could reach an output atom, a
`print` call in a class whose base class the project cannot see, and a
computed `EntryPoint`. `NativeLibrary.GetExport` and
`Marshal.GetDelegateForFunctionPointer` resolve only as catalogue calls;
the function they bind is not followed.

## 4. Languages

```toml output-languages
[[language]]
id = "rust"
status = "supported"
grammar = "tree-sitter-rust"
resolution = ["import-alias", "from-import", "glob-import", "assign-alias", "attr-chain", "macro-path", "macro-wrap", "handle-flow", "path-literal", "fd-literal", "extern-decl", "reexport"]
replacement = "tracing::{trace,debug,info,warn,error}! (a tracing-subscriber layer owns the sink)"

[[language]]
id = "python"
status = "supported"
grammar = "tree-sitter-python"
resolution = ["import-alias", "from-import", "glob-import", "assign-alias", "attr-chain", "builtins-module", "dynamic-getattr", "reexport", "bind-call", "handle-flow", "path-literal", "fd-literal", "extern-decl"]
replacement = "logging.getLogger(__name__) with handlers configured only in the logging module"

[[language]]
id = "javascript"
status = "supported"
grammar = "tree-sitter-javascript"
resolution = ["import-alias", "from-import", "assign-alias", "attr-chain", "dynamic-getattr", "destructure", "bind-call", "global-object", "require", "reexport", "handle-flow", "path-literal", "fd-literal"]
replacement = "a logger module (pino, winston or a project wrapper) configured in one place"

[[language]]
id = "typescript"
status = "supported"
grammar = "tree-sitter-typescript (typescript dialect)"
resolution = ["import-alias", "from-import", "assign-alias", "attr-chain", "dynamic-getattr", "destructure", "bind-call", "global-object", "require", "reexport", "handle-flow", "path-literal", "fd-literal"]
replacement = "the same logger module as javascript"

[[language]]
id = "jsx"
status = "supported"
grammar = "tree-sitter-javascript (jsx enabled)"
resolution = ["import-alias", "from-import", "assign-alias", "attr-chain", "destructure", "bind-call", "global-object", "reexport"]
replacement = "the same logger module as javascript"

[[language]]
id = "tsx"
status = "supported"
grammar = "tree-sitter-typescript (tsx dialect)"
resolution = ["import-alias", "from-import", "assign-alias", "attr-chain", "destructure", "bind-call", "global-object", "reexport"]
replacement = "the same logger module as javascript"

[[language]]
id = "csharp"
status = "supported"
grammar = "tree-sitter-c-sharp"
resolution = ["import-alias", "glob-import", "assign-alias", "attr-chain", "reexport", "handle-flow", "path-literal", "fd-literal", "extern-decl", "bind-call"]
replacement = "Microsoft.Extensions.Logging ILogger<T> (Unity: a project logger over UnityEngine.ILogger)"

[[language]]
id = "java"
status = "planned"
grammar = "tree-sitter-java"
resolution = ["import-alias", "glob-import", "assign-alias", "attr-chain", "reexport", "handle-flow", "path-literal", "fd-literal", "extern-decl", "bind-call"]
replacement = "SLF4J Logger (or System.Logger) with appenders configured in one module"

[[language]]
id = "zig"
status = "planned"
grammar = "tree-sitter-zig"
resolution = ["assign-alias", "attr-chain", "handle-flow", "path-literal", "fd-literal", "extern-decl", "reexport"]
replacement = "std.log scoped loggers with a single std_options.logFn"

[[language]]
id = "c"
status = "planned"
grammar = "tree-sitter-c (also tree-sitter-cpp and CUDA via the cpp grammar)"
resolution = ["macro-wrap", "assign-alias", "handle-flow", "path-literal", "fd-literal", "extern-decl", "reexport"]
replacement = "a project log macro/function over one sink (syslog(3) or a logging library such as zlog or spdlog)"

[[language]]
id = "bash"
status = "planned"
grammar = "tree-sitter-bash"
resolution = ["assign-alias", "redirect-target", "path-literal", "fd-literal", "bind-call"]
replacement = "a single log() function that calls logger(1) or writes to one configured fd"
```

### 4.1 Rust

Notes. Macros are first-class atoms and are imported by name, so
`use std::println as p;` and `std::println!(..)` both resolve to the same
symbol. `write!`/`writeln!` are not atoms by themselves: they are `stream`
atoms that count only when the first argument resolves (through
`handle-flow`) to `io::stdout()`/`io::stderr()` or a `Stdout`/`Stderr`
value. `panic!`, `assert*!`, `unreachable!`, `todo!`, `unimplemented!` and
`.unwrap()/.expect()` failures print to stderr through the panic hook;
they are programmer-bug paths and are advisory. Parsing note: tree-sitter
sees a macro body as a token tree, so the resolver parses the token tree of
`format_args`-family macros only far enough to find the receiver (first
token tree element) of `write!`/`writeln!`.

```toml output-atoms
language = "rust"
atoms = [
 { id = "rust.print", ch = "stdout", sym = "std::print", form = "macro", via = ["macro-path", "import-alias", "macro-wrap"], why = "writes to the global stdout handle", use = "tracing::info!" },
 { id = "rust.println", ch = "stdout", sym = "std::println", form = "macro", via = ["macro-path", "import-alias", "macro-wrap"], why = "writes a line to the global stdout handle", use = "tracing::info!" },
 { id = "rust.eprint", ch = "stderr", sym = "std::eprint", form = "macro", via = ["macro-path", "import-alias", "macro-wrap"], why = "writes to the global stderr handle", use = "tracing::warn! or tracing::error!" },
 { id = "rust.eprintln", ch = "stderr", sym = "std::eprintln", form = "macro", via = ["macro-path", "import-alias", "macro-wrap"], why = "writes a line to the global stderr handle", use = "tracing::warn! or tracing::error!" },
 { id = "rust.dbg", ch = "stderr", sym = "std::dbg", form = "macro", via = ["macro-path", "import-alias", "macro-wrap"], why = "pretty-prints file, line and value to stderr", use = "tracing::debug!(?value)" },
 { id = "rust.write", ch = "stream", sym = "std::write", form = "macro", via = ["macro-path", "handle-flow"], why = "formats into the writer in its first argument; an output when that writer is a std stream", use = "tracing::info!", when = "first arg resolves to Stdout, Stderr, StdoutLock or StderrLock" },
 { id = "rust.writeln", ch = "stream", sym = "std::writeln", form = "macro", via = ["macro-path", "handle-flow"], why = "as write!, with a newline", use = "tracing::info!", when = "first arg resolves to Stdout, Stderr, StdoutLock or StderrLock" },
 { id = "rust.io-stdout", ch = "stdout", sym = "std::io::stdout", form = "fn", via = ["from-import", "import-alias", "glob-import", "handle-flow"], why = "obtains the global stdout handle; every Write method on it is an output", use = "tracing::info!" },
 { id = "rust.io-stderr", ch = "stderr", sym = "std::io::stderr", form = "fn", via = ["from-import", "import-alias", "glob-import", "handle-flow"], why = "obtains the global stderr handle", use = "tracing::warn!" },
 { id = "rust.stdout-type", ch = "stdout", sym = "std::io::{Stdout,StdoutLock}", form = "type", via = ["handle-flow", "import-alias"], why = "a value of these types writes to fd 1 (write, write_all, write_fmt, write_vectored, flush, lock)", use = "tracing::info!" },
 { id = "rust.stderr-type", ch = "stderr", sym = "std::io::{Stderr,StderrLock}", form = "type", via = ["handle-flow", "import-alias"], why = "a value of these types writes to fd 2", use = "tracing::warn!" },
 { id = "rust.io-copy", ch = "stream", sym = "std::io::copy", form = "fn", via = ["from-import", "import-alias"], why = "pumps a reader into a writer; an output when the writer is a std stream", use = "tracing::info!", when = "second arg resolves to a std stream" },
 { id = "rust.bufwriter", ch = "stream", sym = "std::io::{BufWriter,LineWriter}::new", form = "fn", via = ["from-import", "handle-flow"], why = "wraps a writer; wrapping a std stream or a file keeps the output", use = "a tracing layer writer (tracing_appender)", when = "arg resolves to a std stream or file" },
 { id = "rust.fs-write", ch = "file", sym = "std::fs::write", form = "fn", via = ["from-import", "import-alias"], why = "creates and writes a file by path", use = "tracing_appender::rolling or the project log module" },
 { id = "rust.file-create", ch = "file", sym = "std::fs::File::{create,create_new}", form = "fn", via = ["from-import", "import-alias", "handle-flow"], why = "opens a file handle that later writes go to", use = "tracing_appender file writer" },
 { id = "rust.openoptions", ch = "file", sym = "std::fs::OpenOptions", form = "type", via = ["from-import", "import-alias", "handle-flow"], why = "opens a file for write or append", use = "tracing_appender file writer" },
 { id = "rust.file-from-fd", ch = "fd", sym = "std::os::fd::{FromRawFd,OwnedFd,BorrowedFd}::*", form = "fn", via = ["from-import", "fd-literal", "handle-flow"], why = "wraps raw fd 1 or 2 into a File and writes it", use = "tracing::info!", when = "fd argument is 1 or 2" },
 { id = "rust.stdio-fd", ch = "fd", sym = "std::os::fd::AsRawFd::as_raw_fd", form = "method", via = ["handle-flow"], why = "exposes the std stream's fd for out-of-band writes", use = "tracing::info!", sev = "advisory" },
 { id = "rust.path-std", ch = "fd", sym = "std::fs::*", form = "fn", via = ["path-literal"], why = "a path literal such as /dev/stdout, /dev/stderr, /dev/fd/1, /dev/fd/2, /proc/self/fd/1, /proc/self/fd/2 or /dev/tty reaches a std stream", use = "tracing::info!", when = "path resolves to one of the std stream paths" },
 { id = "rust.libc-write", ch = "ffi", sym = "libc::{write,writev,pwrite,send,sendfile}", form = "ffi", via = ["extern-decl", "import-alias", "from-import"], why = "raw syscall write to a descriptor", use = "tracing::info!", when = "fd argument is 1 or 2" },
 { id = "rust.libc-stdio", ch = "ffi", sym = "libc::{printf,puts,putchar,fputs,fputc,putc,fwrite,fprintf,vprintf,vfprintf,dprintf,perror,fflush}", form = "ffi", via = ["extern-decl", "import-alias", "from-import"], why = "C stdio output through the C runtime buffers", use = "tracing::info!" },
 { id = "rust.extern-c", ch = "ffi", sym = "extern \"C\" { fn printf | puts | write | ... }", form = "ffi", via = ["extern-decl"], why = "the program declares its own binding to a C output symbol", use = "tracing::info!" },
 { id = "rust.nix-write", ch = "fd", sym = "nix::unistd::write", form = "fn", via = ["from-import", "import-alias", "fd-literal"], why = "safe wrapper over write(2)", use = "tracing::info!", when = "fd is 1 or 2" },
 { id = "rust.rustix-write", ch = "fd", sym = "rustix::io::{write,writev,pwrite}", form = "fn", via = ["from-import", "import-alias", "fd-literal"], why = "safe wrapper over write(2); rustix::stdio::{stdout,stderr} supplies the fd", use = "tracing::info!" },
 { id = "rust.command", ch = "shell", sym = "std::process::Command::{status,spawn}", form = "method", via = ["handle-flow"], why = "a child inherits the parent's stdout and stderr by default, so its output interleaves with ours", use = "capture with Stdio::piped and log the bytes via tracing::info!" },
 { id = "rust.stdio-inherit", ch = "shell", sym = "std::process::Stdio::inherit", form = "fn", via = ["from-import", "import-alias"], why = "explicitly wires the child to our stdout or stderr", use = "Stdio::piped plus tracing" },
 { id = "rust.command-exec", ch = "shell", sym = "std::os::unix::process::CommandExt::exec", form = "method", via = ["handle-flow"], why = "replaces the process image, child output goes to the inherited stdio", use = "log before exec via tracing::info!", sev = "advisory" },
 { id = "rust.syslog", ch = "syslog", sym = "libc::{syslog,openlog,vsyslog}", form = "ffi", via = ["extern-decl", "import-alias"], why = "writes to the system log directly", use = "a tracing layer (tracing-journald or syslog layer)" },
 { id = "rust.syslog-crate", ch = "syslog", sym = "{syslog,systemd,libsystemd,journald}::*", form = "fn", via = ["import-alias", "from-import"], why = "third-party syslog and journald clients bypass the logging facade", use = "tracing-journald layer" },
 { id = "rust.win-debug", ch = "debugger", sym = "windows_sys::Win32::System::Diagnostics::Debug::{OutputDebugStringA,OutputDebugStringW}", form = "ffi", via = ["from-import", "import-alias"], why = "writes to an attached debugger", use = "tracing layer for the debugger" },
 { id = "rust.win-console", ch = "ffi", sym = "windows_sys::Win32::{System::Console::WriteConsole*,Storage::FileSystem::WriteFile}", form = "ffi", via = ["from-import", "import-alias"], why = "console and handle writes on Windows", use = "tracing::info!" },
 { id = "rust.panic", ch = "implicit", sym = "std::{panic,assert,assert_eq,assert_ne,unreachable,todo,unimplemented}", form = "macro", via = ["macro-path", "import-alias"], why = "failure paths print the message and location to stderr via the panic hook", use = "return Result and log the error; install a panic hook that logs", sev = "advisory" },
 { id = "rust.panic-hook", ch = "implicit", sym = "std::panic::{set_hook,take_hook}", form = "fn", via = ["from-import", "import-alias"], why = "the default hook writes to stderr; a custom hook that prints is an output", use = "a hook that calls tracing::error!", sev = "advisory" },
 { id = "rust.abort", ch = "implicit", sym = "std::process::abort", form = "fn", via = ["from-import", "import-alias"], why = "aborts after the runtime may print to stderr", use = "log then abort", sev = "advisory" },
 { id = "rust.log-crate-fallback", ch = "stderr", sym = "env_logger::*, simple_logger::*, stderrlog::*, pretty_env_logger::*, fern::Dispatch::chain(io::stderr())", form = "fn", via = ["import-alias", "from-import"], why = "logger implementations that write directly to a std stream when initialised outside the configured logging module", use = "initialise the subscriber only in the logging module" },
]
```

### 4.2 Python

Notes. `print` and the std handles are reachable through `builtins`,
`sys`, `sys.__stdout__`, `os` fd calls and `open` on stream paths.
Handle-valued atoms (`sys.stdout`) are matched as attribute loads, so
any method call on the load is an output, including `write`,
`writelines`, `flush`, `buffer.write`, `fileno`, `isatty`. A reassignment
`sys.stdout = x` is itself an atom (it redirects every `print`).
`logging` is the sanctioned facade, but constructing handlers outside the
configured logging module is an output (`logging.StreamHandler()` defaults
to stderr). Detection must treat `getattr(sys, "stdout")`,
`vars(sys)["stdout"]`, `sys.__dict__["stdout"]` and
`importlib.import_module("sys")` as dynamic forms.

```toml output-atoms
language = "python"
atoms = [
 { id = "py.print", ch = "stdout", sym = "builtins.print", form = "builtin", via = ["builtins-module", "assign-alias", "dynamic-getattr", "reexport", "bind-call"], why = "writes to sys.stdout (or file=)", use = "logger.info" },
 { id = "py.input", ch = "stdout", sym = "builtins.input", form = "builtin", via = ["builtins-module", "assign-alias"], why = "writes its prompt argument to stdout", use = "read stdin without a prompt; log the question with logger.info", sev = "advisory" },
 { id = "py.help", ch = "stdout", sym = "builtins.help", form = "builtin", via = ["builtins-module"], why = "pages documentation to stdout", use = "none in library code", sev = "advisory" },
 { id = "py.breakpoint", ch = "debugger", sym = "builtins.breakpoint", form = "builtin", via = ["builtins-module"], why = "enters pdb and writes to the std streams", use = "remove before commit; log instead", sev = "advisory" },
 { id = "py.sys-stdout", ch = "stdout", sym = "sys.stdout", form = "attr", via = ["import-alias", "from-import", "dynamic-getattr", "assign-alias", "handle-flow"], why = "text stream on fd 1; write, writelines, flush, buffer, fileno all count", use = "logger.info" },
 { id = "py.sys-stderr", ch = "stderr", sym = "sys.stderr", form = "attr", via = ["import-alias", "from-import", "dynamic-getattr", "assign-alias", "handle-flow"], why = "text stream on fd 2", use = "logger.warning or logger.error" },
 { id = "py.sys-dunder-stdout", ch = "stdout", sym = "sys.__stdout__", form = "attr", via = ["import-alias", "from-import", "dynamic-getattr"], why = "the original stdout, immune to redirect_stdout", use = "logger.info" },
 { id = "py.sys-dunder-stderr", ch = "stderr", sym = "sys.__stderr__", form = "attr", via = ["import-alias", "from-import", "dynamic-getattr"], why = "the original stderr", use = "logger.error" },
 { id = "py.sys-assign", ch = "implicit", sym = "sys.{stdout,stderr} = <expr>", form = "attr", via = ["import-alias", "from-import"], why = "rebinding the streams redirects every print and write in the process", use = "configure a logging handler instead", sev = "advisory" },
 { id = "py.os-write", ch = "fd", sym = "os.{write,writev,pwrite,sendfile}", form = "fn", via = ["import-alias", "from-import", "fd-literal", "dynamic-getattr"], why = "raw write to a descriptor", use = "logger.info", when = "fd is 1, 2, sys.stdout.fileno() or sys.stderr.fileno()" },
 { id = "py.os-fdopen", ch = "fd", sym = "os.fdopen", form = "fn", via = ["import-alias", "from-import", "fd-literal"], why = "opens fd 1 or 2 as a file object", use = "logger.info", when = "fd is 1 or 2" },
 { id = "py.os-dup", ch = "fd", sym = "os.{dup,dup2}", form = "fn", via = ["import-alias", "from-import", "fd-literal"], why = "duplicates or rewires std fds so later writes escape the facade", use = "none", when = "an argument is 1 or 2", sev = "advisory" },
 { id = "py.open", ch = "file", sym = "builtins.open", form = "builtin", via = ["builtins-module", "assign-alias"], why = "opens a path for writing; in write, append or exclusive modes it is a file sink; with a std stream path or fd 1/2 it is a std stream", use = "logging.FileHandler built in the logging module", mode_arg = 1 },
 { id = "py.io-open", ch = "file", sym = "io.{open,FileIO,open_code}", form = "fn", via = ["import-alias", "from-import"], why = "same as open", use = "logging.FileHandler in the logging module", mode_arg = 1 },
 { id = "py.path-std", ch = "fd", sym = "open | io.open | pathlib.Path | os.open | shutil.copyfile | builtins.open", form = "fn", via = ["path-literal"], why = "a path literal /dev/stdout, /dev/stderr, /dev/fd/1, /dev/fd/2, /proc/self/fd/1, /proc/self/fd/2, /dev/tty or /dev/console names a std stream", use = "logger.info", when = "path resolves to a std stream path" },
 { id = "py.pathlib-write", ch = "file", sym = "pathlib.Path.{write_text,write_bytes,touch}", form = "method", via = ["import-alias", "from-import", "handle-flow"], why = "writes a file by path", use = "logging.FileHandler in the logging module" },
 { id = "py.pathlib-open", ch = "file", sym = "pathlib.Path.open", form = "method", via = ["import-alias", "from-import", "handle-flow"], why = "opens a file by path in a writing mode", use = "logging.FileHandler in the logging module", mode_arg = 0 },
 { id = "py.os-open", ch = "file", sym = "os.open", form = "fn", via = ["import-alias", "from-import"], why = "opens a descriptor with O_WRONLY or O_RDWR", use = "logging.FileHandler in the logging module", when = "flags include O_WRONLY, O_RDWR, O_APPEND or O_CREAT" },
 { id = "py.shutil", ch = "stream", sym = "shutil.{copyfileobj,copyfile,copy,copy2}", form = "fn", via = ["import-alias", "from-import"], why = "pumps bytes into a destination; an output when it is a std stream or a file", use = "logger.info", when = "destination resolves to a std stream or file" },
 { id = "py.json-dump", ch = "stream", sym = "json.dump", form = "fn", via = ["import-alias", "from-import"], why = "serialises into a file object; an output when that object is a std stream or file", use = "logger.info(json.dumps(...))", when = "second arg resolves to a std stream or file" },
 { id = "py.csv-writer", ch = "stream", sym = "csv.{writer,DictWriter}", form = "fn", via = ["import-alias", "from-import"], why = "writes rows to a file object", use = "logger.info", when = "first arg resolves to a std stream or file" },
 { id = "py.pickle-dump", ch = "stream", sym = "{pickle,marshal,plistlib,tomli_w,yaml}.dump", form = "fn", via = ["import-alias", "from-import"], why = "serialises into a file object", use = "logger.info", when = "file arg resolves to a std stream or file", sev = "advisory" },
 { id = "py.redirect", ch = "stream", sym = "contextlib.{redirect_stdout,redirect_stderr}", form = "type", via = ["import-alias", "from-import"], why = "swaps sys.stdout or sys.stderr to a target; the target is a sink", use = "capture into a buffer and log it with logger.info" },
 { id = "py.traceback", ch = "stderr", sym = "traceback.{print_exc,print_exception,print_stack,print_tb,print_last,print_list,TracebackException.print}", form = "fn", via = ["import-alias", "from-import"], why = "prints the traceback to sys.stderr unless file= is given", use = "logger.exception or logger.error(exc_info=True)" },
 { id = "py.pprint", ch = "stdout", sym = "pprint.{pprint,pp,PrettyPrinter}", form = "fn", via = ["import-alias", "from-import"], why = "pretty-prints to sys.stdout or the stream argument", use = "logger.info(pprint.pformat(x))" },
 { id = "py.warnings", ch = "stderr", sym = "warnings.{warn,warn_explicit,showwarning,_showwarnmsg}", form = "fn", via = ["import-alias", "from-import"], why = "the default filter prints to sys.stderr", use = "logging.captureWarnings(True) plus logger.warning" },
 { id = "py.excepthook", ch = "implicit", sym = "sys.{excepthook,__excepthook__,unraisablehook,__unraisablehook__}, threading.excepthook", form = "attr", via = ["import-alias", "from-import"], why = "the default hooks print the uncaught exception to stderr", use = "install a hook that calls logger.critical", sev = "advisory" },
 { id = "py.displayhook", ch = "stdout", sym = "sys.{displayhook,__displayhook__}", form = "attr", via = ["import-alias", "from-import"], why = "the default hook prints expression results to stdout", use = "none outside the REPL", sev = "advisory" },
 { id = "py.faulthandler", ch = "stderr", sym = "faulthandler.{enable,dump_traceback,dump_traceback_later,register}", form = "fn", via = ["import-alias", "from-import"], why = "writes tracebacks to a file or stderr", use = "route through logging via a handler fd owned by the logging module", sev = "advisory" },
 { id = "py.pstats", ch = "stdout", sym = "{pstats.Stats.print_stats,pstats.Stats.print_callers,cProfile.run,profile.run,timeit.main,trace.Trace.results,dis.dis,dis.show_code,inspect.getsource}", form = "method", via = ["import-alias", "from-import", "handle-flow"], why = "profilers and disassemblers print to stdout by default", use = "pass stream= a StringIO and log it", sev = "advisory" },
 { id = "py.cmd", ch = "stdout", sym = "{cmd.Cmd.stdout,code.interact,pdb.set_trace,pdb.post_mortem,site.quit,unittest.TextTestRunner,doctest.testmod,pydoc.help}", form = "fn", via = ["import-alias", "from-import"], why = "interactive and test frameworks print to the std streams", use = "pass stream= and log, or configure the runner in tests only", sev = "advisory" },
 { id = "py.http-server", ch = "stderr", sym = "http.server.BaseHTTPRequestHandler.{log_message,log_error,log_request}", form = "method", via = ["import-alias", "from-import"], why = "the stdlib request logger writes access lines to stderr", use = "override to call logger.info", sev = "advisory" },
 { id = "py.logging-stream", ch = "stream", sym = "logging.{StreamHandler,lastResort,basicConfig}", form = "type", via = ["import-alias", "from-import", "reexport"], why = "StreamHandler() defaults to stderr; basicConfig(stream=) and the last-resort handler write to a std stream; allowed only inside the configured logging module", use = "build handlers in the logging module only" },
 { id = "py.logging-file", ch = "file", sym = "logging.{FileHandler,handlers.WatchedFileHandler,handlers.RotatingFileHandler,handlers.TimedRotatingFileHandler,basicConfig,config.dictConfig,config.fileConfig}", form = "type", via = ["import-alias", "from-import", "reexport"], why = "file sinks built outside the configured module", use = "build handlers in the logging module only" },
 { id = "py.logging-remote", ch = "syslog", sym = "logging.handlers.{SysLogHandler,NTEventLogHandler,SocketHandler,DatagramHandler,SMTPHandler,HTTPHandler,QueueHandler,MemoryHandler}", form = "type", via = ["import-alias", "from-import"], why = "network and system sinks built outside the logging module", use = "build handlers in the logging module only" },
 { id = "py.syslog", ch = "syslog", sym = "syslog.{syslog,openlog}, systemd.journal.{send,JournalHandler}, win32evtlogutil.ReportEvent", form = "fn", via = ["import-alias", "from-import"], why = "writes straight to the system log", use = "logging.handlers.SysLogHandler in the logging module" },
 { id = "py.subprocess", ch = "shell", sym = "subprocess.{run,call,check_call,check_output,Popen,getoutput,getstatusoutput}", form = "fn", via = ["import-alias", "from-import", "reexport"], why = "stdout and stderr are inherited unless captured; check_output(stderr=) and stdout=sys.stdout also wire to the std streams", use = "capture=True or stdout=PIPE and log the output" },
 { id = "py.os-process", ch = "shell", sym = "os.{system,popen,execv,execve,execvp,execl,execlp,spawnv,spawnl,posix_spawn,startfile}", form = "fn", via = ["import-alias", "from-import"], why = "child output goes to the inherited stdio", use = "subprocess with captured pipes and logger.info" },
 { id = "py.asyncio-proc", ch = "shell", sym = "asyncio.{create_subprocess_exec,create_subprocess_shell}", form = "fn", via = ["import-alias", "from-import"], why = "same inheritance as subprocess", use = "stdout=PIPE and log" },
 { id = "py.ctypes", ch = "ffi", sym = "ctypes.{CDLL,cdll,PyDLL,pydll,windll,WinDLL,pythonapi,cast}", form = "ffi", via = ["extern-decl", "import-alias", "from-import", "dynamic-getattr"], why = "loads libc, kernel32 or the interpreter and calls printf, puts, write, PySys_WriteStdout, PySys_WriteStderr, OutputDebugStringA", use = "logger.info" },
 { id = "py.cffi", ch = "ffi", sym = "cffi.FFI.{cdef,dlopen,verify}", form = "ffi", via = ["extern-decl", "import-alias"], why = "declares and calls C output functions", use = "logger.info" },
 { id = "py.rich", ch = "stdout", sym = "{rich.print,rich.console.Console,rich.pretty.pprint,rich.progress.*,click.echo,click.secho,click.echo_via_pager,tqdm.tqdm,typer.echo,colorama.*,termcolor.cprint,tabulate.*}", form = "fn", via = ["import-alias", "from-import", "reexport"], why = "third-party printers write to stdout or stderr", use = "logger plus a rich handler configured in the logging module" },
 { id = "py.curses", ch = "stdout", sym = "{curses.*,msvcrt.putch,msvcrt.putwch,tty.*,readline.write_history_file}", form = "fn", via = ["import-alias", "from-import"], why = "terminal output outside print", use = "none outside a TUI module", sev = "advisory" },
 { id = "py.builtins-dict", ch = "stdout", sym = "builtins.__dict__ | vars(builtins) | __builtins__", form = "attr", via = ["builtins-module", "dynamic-getattr"], why = "dictionary access to print", use = "logger.info" },
]
```

### 4.3 JavaScript, TypeScript, JSX, TSX

The four web dialects share one table (the ids carry the `js.` prefix
and apply to every dialect; the resolver loads the dialect's grammar from
`output-languages`). Node, Deno, Bun and browser globals are all listed;
the rule scopes by the project's configured runtime. `console` is a
global, so the resolver treats an unbound `console` identifier as
`globalThis.console` and a locally bound `console` as shadowed.

```toml output-atoms
language = "javascript"
atoms = [
 { id = "js.console-log", ch = "stdout", sym = "console.{log,info,debug,table,dir,dirxml,group,groupCollapsed,groupEnd,count,countReset,time,timeEnd,timeLog,timeStamp,profile,profileEnd,clear}", form = "method", via = ["global-object", "destructure", "bind-call", "assign-alias", "dynamic-getattr", "import-alias", "require", "reexport"], why = "console writes to stdout (Node) or the devtools console (browsers)", use = "logger.info or logger.debug" },
 { id = "js.console-err", ch = "stderr", sym = "console.{error,warn,trace,assert}", form = "method", via = ["global-object", "destructure", "bind-call", "assign-alias", "dynamic-getattr", "import-alias", "require", "reexport"], why = "console writes to stderr (Node)", use = "logger.warn or logger.error" },
 { id = "js.console-ctor", ch = "stream", sym = "console.Console, require('console').Console, node:console.Console", form = "type", via = ["require", "import-alias", "from-import", "global-object"], why = "builds a console over arbitrary streams, normally process.stdout and process.stderr", use = "the project logger" },
 { id = "js.console-module", ch = "stdout", sym = "node:console", form = "type", via = ["require", "import-alias", "from-import"], why = "importing the module binds the same console object", use = "the project logger" },
 { id = "js.console-global", ch = "stdout", sym = "globalThis.console | window.console | self.console | global.console", form = "attr", via = ["global-object", "assign-alias", "dynamic-getattr"], why = "global spellings of console", use = "the project logger" },
 { id = "js.process-stdout", ch = "stdout", sym = "process.stdout.{write,end,cork,uncork}", form = "method", via = ["global-object", "dynamic-getattr", "destructure", "from-import", "require", "handle-flow", "assign-alias"], why = "stream on fd 1", use = "logger.info" },
 { id = "js.process-stderr", ch = "stderr", sym = "process.stderr.{write,end}", form = "method", via = ["global-object", "dynamic-getattr", "destructure", "from-import", "require", "handle-flow", "assign-alias"], why = "stream on fd 2", use = "logger.error" },
 { id = "js.process-internal", ch = "stderr", sym = "process.{_rawDebug,binding,_linkedBinding,stdout._handle,stderr._handle,stdout._write,stderr._write,stdout._writev,stderr._writev}", form = "method", via = ["global-object", "destructure", "require", "assign-alias"], why = "process internals write straight to fd 1 or 2 without the public stream API (_rawDebug writes to stderr)", use = "logger" },
 { id = "js.process-import", ch = "stdout", sym = "node:process.{stdout,stderr}", form = "attr", via = ["from-import", "import-alias", "require"], why = "named export forms of the same streams", use = "logger" },
 { id = "js.process-warning", ch = "stderr", sym = "process.{emitWarning,on('warning')}", form = "fn", via = ["global-object", "from-import"], why = "default handler prints the warning to stderr", use = "logger.warn", sev = "advisory" },
 { id = "js.pipe", ch = "stream", sym = "stream.{pipe,pipeline,finished}, stream/promises.pipeline, Readable.prototype.pipe", form = "method", via = ["handle-flow", "from-import", "require"], why = "a pipeline whose sink is process.stdout, process.stderr or a file stream", use = "logger", when = "sink resolves to a std stream or file" },
 { id = "js.fs-writesync", ch = "fd", sym = "fs.{writeSync,write,writevSync,writev}", form = "fn", via = ["require", "import-alias", "from-import", "fd-literal", "dynamic-getattr"], why = "raw descriptor write", use = "logger", when = "fd is 1 or 2 or process.stdout.fd / process.stderr.fd" },
 { id = "js.fs-file", ch = "file", sym = "fs.{writeFile,writeFileSync,appendFile,appendFileSync,createWriteStream,copyFile,cp,truncate}, fs.promises.{writeFile,appendFile}, FileHandle.{write,writeFile,appendFile,createWriteStream}", form = "fn", via = ["require", "import-alias", "from-import", "destructure"], why = "file sinks by path or fd", use = "the file transport of the project logger" },
 { id = "js.fs-open", ch = "file", sym = "fs.{open,openSync}, fs.promises.open", form = "fn", via = ["require", "import-alias", "from-import", "destructure"], why = "opens a file descriptor in a writing flag mode", use = "the file transport of the project logger", mode_arg = 1 },
 { id = "js.path-std", ch = "fd", sym = "fs.*", form = "fn", via = ["path-literal"], why = "a path literal /dev/stdout, /dev/stderr, /dev/fd/1, /dev/fd/2, /proc/self/fd/1, /dev/tty, CON, or an options bag {fd: 1} / {fd: 2} names a std stream", use = "logger", when = "path or fd resolves to a std stream" },
 { id = "js.child-process", ch = "shell", sym = "child_process.{spawn,spawnSync,exec,execSync,execFile,execFileSync,fork}", form = "fn", via = ["require", "import-alias", "from-import", "destructure"], why = "stdio:'inherit' (and spawnSync/execSync defaults for stderr) wires the child to our streams", use = "stdio:'pipe' and log the captured data" },
 { id = "js.readline", ch = "stdout", sym = "readline.{createInterface,Interface.write,Interface.setPrompt,Interface.prompt,Interface.question,cursorTo,clearLine,moveCursor,emitKeypressEvents}, readline/promises.*", form = "method", via = ["require", "import-alias", "from-import", "handle-flow"], why = "writes prompts and cursor controls to the output stream", use = "logger for messages; keep prompts in a CLI module", sev = "advisory" },
 { id = "js.tty", ch = "stdout", sym = "tty.WriteStream, process.stdout.{columns,getWindowSize,clearLine,cursorTo}", form = "type", via = ["require", "import-alias", "handle-flow"], why = "terminal stream writers", use = "logger", sev = "advisory" },
 { id = "js.inspector", ch = "debugger", sym = "inspector.console.{log,warn,error,...}, node:inspector.Session.post('Runtime.consoleAPICalled')", form = "method", via = ["require", "import-alias", "from-import"], why = "writes to the attached inspector without touching stdio", use = "logger" },
 { id = "js.debugger-stmt", ch = "debugger", sym = "debugger", form = "fn", via = [], why = "breakpoint statement left in code", use = "remove", sev = "advisory" },
 { id = "js.util", ch = "stderr", sym = "util.{debuglog,debug,log,printf},node:util.debuglog", form = "fn", via = ["require", "import-alias", "from-import"], why = "debuglog writes to stderr when NODE_DEBUG matches; util.log wrote to stdout", use = "logger.debug" },
 { id = "js.diagnostics", ch = "stderr", sym = "process.{report.writeReport,binding},v8.{writeHeapSnapshot,setFlagsFromString},worker_threads.parentPort.postMessage(console)", form = "fn", via = ["global-object", "require"], why = "diagnostic dumps to files or stderr", use = "logger", sev = "advisory" },
 { id = "js.worker-stdio", ch = "stdout", sym = "worker_threads.Worker({stdout, stderr})", form = "type", via = ["require", "import-alias"], why = "worker stdio forwarded to the parent's streams", use = "logger", sev = "advisory" },
 { id = "js.deno", ch = "stdout", sym = "Deno.{stdout,stderr}.{write,writeSync,writable}, Deno.{writeTextFile,writeTextFileSync,writeFile,writeFileSync,open,create,openSync,createSync}, Deno.Command", form = "method", via = ["global-object", "assign-alias", "handle-flow"], why = "Deno std stream and file writers and child process inheritance", use = "std/log" },
 { id = "js.bun", ch = "stdout", sym = "Bun.{write,stdout,stderr,spawn,spawnSync,file(...).writer}", form = "fn", via = ["global-object", "assign-alias", "handle-flow"], why = "Bun std stream and file writers", use = "the project logger" },
 { id = "js.dom-alert", ch = "stdout", sym = "window.{alert,confirm,prompt,print}", form = "fn", via = ["global-object", "assign-alias", "dynamic-getattr"], why = "browser modal and print output", use = "UI component for users; logger for diagnostics", sev = "advisory" },
 { id = "js.dom-write", ch = "stdout", sym = "document.{write,writeln}", form = "method", via = ["global-object", "assign-alias"], why = "writes into the document stream", use = "DOM APIs; logger for diagnostics", sev = "advisory" },
 { id = "js.beacon", ch = "syslog", sym = "navigator.sendBeacon, fetch, XMLHttpRequest, WebSocket.send, EventSource", form = "fn", via = ["global-object", "assign-alias"], why = "shipping log lines straight to a collector bypasses the facade; reported only when the URL or payload is a log endpoint", use = "logger transport", when = "url resolves to a configured log endpoint", sev = "advisory" },
 { id = "js.storage-log", ch = "file", sym = "localStorage.setItem, indexedDB, caches.put used as a log buffer", form = "method", via = ["global-object"], why = "ad hoc persisted logs", use = "logger transport", sev = "advisory" },
 { id = "js.logger-lib", ch = "stdout", sym = "{pino,winston,bunyan,log4js,loglevel,debug,consola,signale,npmlog,chalk,ora,cli-progress}.*", form = "fn", via = ["require", "import-alias", "from-import", "reexport"], why = "logging and printing libraries write to the std streams; allowed only where the project logger configures them", use = "configure once in the logging module", sev = "advisory" },
 { id = "js.syslog-lib", ch = "syslog", sym = "{syslog-client,node-syslog,winston-syslog,systemd-journald,node-windows.EventLogger}.*", form = "fn", via = ["require", "import-alias", "from-import"], why = "system log sinks", use = "logger transport" },
 { id = "js.napi", ch = "ffi", sym = "{ffi-napi,koffi,node-ffi,bun:ffi,Deno.dlopen,process.dlopen}.*", form = "ffi", via = ["require", "import-alias", "global-object"], why = "calls libc printf or write", use = "logger" },
 { id = "js.wasm-import", ch = "ffi", sym = "WebAssembly.instantiate importObject.{fd_write,env.printf,env.puts}, wasi.WASI", form = "ffi", via = ["global-object"], why = "WASI fd_write wires guest output to host streams", use = "route through logger", sev = "advisory" },
 { id = "js.dynamic", ch = "stdout", sym = "eval | Function(...) | new Function | vm.runInContext", form = "fn", via = ["dynamic-getattr"], why = "code built at run time can reach any atom; reported as unresolved-dynamic", use = "avoid", sev = "advisory" },
]
```

### 4.4 C# (including Unity)

Notes. `System.Console` is a static class, so `using static System.Console;`
turns bare `WriteLine(..)` into an atom, and `using C = System.Console;`
aliases it. `Console.Out` and `Console.Error` are `TextWriter` values; the
resolver follows them through `handle-flow` (assignment to a local or
field). Unity's `Debug` is `UnityEngine.Debug`; `System.Diagnostics.Debug`
is a different symbol and the resolver must pick by the `using` that is in
scope. `MonoBehaviour.print` is inherited, so a bare `print(..)` inside a
subclass resolves to it.

```toml output-atoms
language = "csharp"
atoms = [
 { id = "cs.console-write", ch = "stdout", sym = "System.Console.{Write,WriteLine}", form = "method", via = ["import-alias", "glob-import", "attr-chain"], why = "writes to Console.Out", use = "ILogger.LogInformation" },
 { id = "cs.console-out", ch = "stdout", sym = "System.Console.Out", form = "attr", via = ["import-alias", "glob-import", "attr-chain", "handle-flow", "assign-alias"], why = "the stdout TextWriter; Write, WriteLine, Flush and WriteAsync all count", use = "ILogger" },
 { id = "cs.console-err", ch = "stderr", sym = "System.Console.Error", form = "attr", via = ["import-alias", "glob-import", "attr-chain", "handle-flow", "assign-alias"], why = "the stderr TextWriter", use = "ILogger.LogError" },
 { id = "cs.console-stream", ch = "fd", sym = "System.Console.{OpenStandardOutput,OpenStandardError}", form = "fn", via = ["import-alias", "glob-import", "attr-chain", "handle-flow"], why = "raw Stream over fd 1 or 2", use = "ILogger" },
 { id = "cs.console-set", ch = "implicit", sym = "System.Console.{SetOut,SetError}", form = "fn", via = ["import-alias", "glob-import", "attr-chain"], why = "redirects the console writers", use = "configure logging providers", sev = "advisory" },
 { id = "cs.console-ui", ch = "stdout", sym = "System.Console.{Beep,Clear,SetCursorPosition,ForegroundColor,ResetColor,WindowWidth,Title,ReadKey}", form = "attr", via = ["import-alias", "glob-import"], why = "terminal control writes escape sequences or modifies the console", use = "a CLI presentation module", sev = "advisory" },
 { id = "cs.debug", ch = "debugger", sym = "System.Diagnostics.Debug.{Write,WriteLine,WriteIf,WriteLineIf,Print,Assert,Fail}", form = "method", via = ["import-alias", "glob-import", "attr-chain"], why = "writes to attached trace listeners and the debugger (compiled only in DEBUG)", use = "ILogger.LogDebug" },
 { id = "cs.trace", ch = "debugger", sym = "System.Diagnostics.Trace.{Write,WriteLine,WriteIf,WriteLineIf,TraceInformation,TraceWarning,TraceError,Assert,Fail}", form = "method", via = ["import-alias", "glob-import", "attr-chain"], why = "writes to Trace.Listeners (default listener goes to the debugger)", use = "ILogger" },
 { id = "cs.tracesource", ch = "debugger", sym = "System.Diagnostics.{TraceSource,TextWriterTraceListener,ConsoleTraceListener,DefaultTraceListener,EventLogTraceListener,DelimitedListTraceListener,XmlWriterTraceListener}", form = "type", via = ["import-alias", "glob-import", "handle-flow"], why = "trace listeners that write to console, files or the event log", use = "logging providers" },
 { id = "cs.debugger", ch = "debugger", sym = "System.Diagnostics.Debugger.{Log,Break,Launch}", form = "method", via = ["import-alias", "glob-import", "attr-chain"], why = "debugger channel and breakpoints", use = "ILogger.LogDebug", sev = "advisory" },
 { id = "cs.eventlog", ch = "syslog", sym = "System.Diagnostics.{EventLog.WriteEntry,EventLog.WriteEvent,EventSource.WriteEvent,Tracing.EventSource}", form = "method", via = ["import-alias", "glob-import", "handle-flow"], why = "Windows event log and ETW", use = "Microsoft.Extensions.Logging.EventLog provider" },
 { id = "cs.mel-console", ch = "stdout", sym = "Microsoft.Extensions.Logging.{ConsoleLoggerExtensions.AddConsole,AddSimpleConsole,AddJsonConsole,AddSystemdConsole,AddDebug,AddEventSourceLogger,AddEventLog}", form = "fn", via = ["import-alias", "glob-import"], why = "provider registration is a sink choice; allowed only in the logging composition root", use = "register in the logging module only" },
 { id = "cs.file-write", ch = "file", sym = "System.IO.File.{WriteAllText,WriteAllLines,WriteAllBytes,AppendAllText,AppendAllLines,AppendText,Create,CreateText,OpenWrite,Open,WriteAllTextAsync,WriteAllLinesAsync,WriteAllBytesAsync,AppendAllTextAsync,Replace,Copy}", form = "fn", via = ["import-alias", "glob-import", "attr-chain"], why = "writes a file by path", use = "a file logging provider (Serilog or MEL file sink) in the logging module" },
 { id = "cs.streams", ch = "file", sym = "System.IO.{FileStream,StreamWriter,BinaryWriter,FileInfo.CreateText,FileInfo.AppendText,FileInfo.OpenWrite,MemoryMappedFile.CreateFromFile}", form = "type", via = ["import-alias", "glob-import", "handle-flow"], why = "file handles and writers", use = "a file logging provider" },
 { id = "cs.path-std", ch = "fd", sym = "System.IO.{File,FileStream,StreamWriter}.*", form = "fn", via = ["path-literal", "fd-literal"], why = "a path literal /dev/stdout, /dev/stderr, /dev/fd/1, /dev/fd/2, /proc/self/fd/1, CONOUT$ or new FileStream(new SafeFileHandle((IntPtr)1,false), FileAccess.Write) reaches a std stream", use = "ILogger", when = "path or handle resolves to a std stream" },
 { id = "cs.textwriter", ch = "stream", sym = "System.IO.TextWriter.Synchronized, System.IO.StringWriter used with Console.SetOut", form = "fn", via = ["import-alias", "glob-import", "handle-flow"], why = "wraps a std writer without changing its destination", use = "ILogger", when = "arg resolves to Console.Out or Console.Error", sev = "advisory" },
 { id = "cs.process", ch = "shell", sym = "System.Diagnostics.Process.Start, ProcessStartInfo{UseShellExecute,RedirectStandardOutput,RedirectStandardError}", form = "fn", via = ["import-alias", "glob-import", "handle-flow"], why = "a started process inherits our console unless output is redirected", use = "RedirectStandardOutput = true and log the lines" },
 { id = "cs.pinvoke", ch = "ffi", sym = "System.Runtime.InteropServices.DllImport.*.{write,writev,printf,puts,putchar,fputs,fwrite,WriteFile,WriteConsole,WriteConsoleW,OutputDebugString,OutputDebugStringA,OutputDebugStringW,syslog,openlog}", form = "ffi", via = ["extern-decl", "import-alias"], why = "calls native output functions", use = "ILogger" },
 { id = "cs.libimport", ch = "ffi", sym = "System.Runtime.InteropServices.{LibraryImport,Marshal.GetDelegateForFunctionPointer,NativeLibrary.GetExport}", form = "ffi", via = ["extern-decl", "import-alias", "handle-flow"], why = "source-generated and dynamic native bindings to the same functions", use = "ILogger" },
 { id = "cs.failfast", ch = "implicit", sym = "System.Environment.FailFast", form = "fn", via = ["import-alias", "glob-import", "attr-chain"], why = "writes the message and stack to stderr before aborting", use = "log then FailFast", sev = "advisory" },
 { id = "cs.unhandled", ch = "implicit", sym = "System.AppDomain.UnhandledException, System.Exception.ToString printed by the host", form = "attr", via = ["import-alias", "glob-import"], why = "the runtime prints unhandled exceptions to stderr", use = "handler that calls ILogger.LogCritical", sev = "advisory" },
 { id = "cs.unity-debug", ch = "debugger", sym = "UnityEngine.Debug.{Log,LogWarning,LogError,LogException,LogAssertion,LogFormat,LogWarningFormat,LogErrorFormat,LogAssertionFormat,Assert,AssertFormat,unityLogger}", form = "method", via = ["import-alias", "glob-import", "attr-chain", "assign-alias"], why = "Unity console and Player.log sink", use = "a project logger over UnityEngine.ILogger (Debug.unityLogger) used from one logging module" },
 { id = "cs.unity-print", ch = "debugger", sym = "UnityEngine.MonoBehaviour.print", form = "method", via = ["attr-chain"], why = "inherited helper that forwards to Debug.Log", use = "the project logger" },
 { id = "cs.unity-logger", ch = "debugger", sym = "UnityEngine.{Logger,ILogger,ILogHandler,DebugLogHandler}.{Log,LogFormat,LogException}", form = "method", via = ["import-alias", "glob-import", "handle-flow"], why = "Unity logger objects not owned by the logging module", use = "the project logger" },
 { id = "cs.unity-draw", ch = "debugger", sym = "UnityEngine.Debug.{DrawLine,DrawRay,Break,ClearDeveloperConsole}", form = "method", via = ["import-alias", "glob-import", "attr-chain"], why = "editor-only debug overlays and breaks", use = "gizmos behind #if UNITY_EDITOR", sev = "advisory" },
 { id = "cs.unity-ui", ch = "stdout", sym = "UnityEngine.GUILayout/GUI/IMGUI text, UnityEditor.EditorUtility.DisplayDialog", form = "method", via = ["import-alias", "glob-import"], why = "user-facing text, not logging; listed so the rule can exempt it by symbol", use = "none (exempt)", sev = "advisory" },
 { id = "cs.serilog", ch = "stdout", sym = "{Serilog.Log,Serilog.LoggerConfiguration.WriteTo.{Console,File,Debug,Trace,EventLog,Syslog},NLog.*,log4net.*}", form = "fn", via = ["import-alias", "glob-import", "reexport"], why = "third-party logging sinks configured outside the logging module", use = "configure in the logging module only", sev = "advisory" },
]
```

### 4.5 Java (planned)

```toml output-atoms
language = "java"
atoms = [
 { id = "java.system-out", ch = "stdout", sym = "java.lang.System.out.{print,println,printf,format,write,append,flush,checkError}", form = "method", via = ["import-alias", "glob-import", "attr-chain", "handle-flow", "assign-alias"], why = "PrintStream on fd 1", use = "SLF4J logger.info" },
 { id = "java.system-err", ch = "stderr", sym = "java.lang.System.err.{print,println,printf,format,write,append,flush}", form = "method", via = ["import-alias", "glob-import", "attr-chain", "handle-flow", "assign-alias"], why = "PrintStream on fd 2", use = "SLF4J logger.error" },
 { id = "java.system-set", ch = "implicit", sym = "java.lang.System.{setOut,setErr}", form = "fn", via = ["import-alias", "attr-chain"], why = "redirects the std PrintStreams", use = "configure appenders", sev = "advisory" },
 { id = "java.console", ch = "stdout", sym = "java.lang.System.console().{writer,printf,format,readLine,readPassword}, java.io.Console", form = "method", via = ["handle-flow", "import-alias"], why = "console writer and printf (prompts on readLine and readPassword)", use = "logger", sev = "advisory" },
 { id = "java.filedescriptor", ch = "fd", sym = "java.io.FileDescriptor.{out,err}, new FileOutputStream(FileDescriptor.out)", form = "attr", via = ["import-alias", "attr-chain", "handle-flow"], why = "raw stream over fd 1 or 2", use = "logger" },
 { id = "java.stacktrace", ch = "stderr", sym = "java.lang.Throwable.{printStackTrace,setStackTrace}, java.lang.Thread.dumpStack, StackWalker consumers that print", form = "method", via = ["handle-flow"], why = "printStackTrace() with no argument writes to System.err", use = "logger.error(msg, throwable)" },
 { id = "java.uncaught", ch = "implicit", sym = "java.lang.Thread.{setDefaultUncaughtExceptionHandler,UncaughtExceptionHandler}", form = "fn", via = ["import-alias"], why = "default handler prints to stderr", use = "handler that calls logger.error", sev = "advisory" },
 { id = "java.files", ch = "file", sym = "java.nio.file.Files.{write,writeString,newBufferedWriter,newOutputStream,createFile,copy,move}", form = "fn", via = ["import-alias", "glob-import", "attr-chain"], why = "writes a file by path", use = "file appender in the logging module" },
 { id = "java.io-file", ch = "file", sym = "java.io.{FileOutputStream,FileWriter,PrintWriter,PrintStream,RandomAccessFile,BufferedWriter,OutputStreamWriter,ObjectOutputStream}", form = "type", via = ["import-alias", "glob-import", "handle-flow"], why = "file and stream writers; PrintStream/PrintWriter(System.out) wrap a std stream", use = "file appender in the logging module" },
 { id = "java.path-std", ch = "fd", sym = "java.nio.file.Path.of | Paths.get | new File | new FileOutputStream", form = "fn", via = ["path-literal"], why = "/dev/stdout, /dev/stderr, /proc/self/fd/1 or CONOUT$ names a std stream", use = "logger", when = "path resolves to a std stream path" },
 { id = "java.process", ch = "shell", sym = "java.lang.{ProcessBuilder.inheritIO,ProcessBuilder.redirectOutput(Redirect.INHERIT),ProcessBuilder.redirectError(Redirect.INHERIT),Runtime.exec}", form = "method", via = ["import-alias", "handle-flow"], why = "child stdio inherited", use = "Redirect.PIPE and log the lines" },
 { id = "java.jul", ch = "stderr", sym = "java.util.logging.{ConsoleHandler,StreamHandler,FileHandler,SocketHandler,MemoryHandler,LogManager.readConfiguration}", form = "type", via = ["import-alias", "glob-import"], why = "handlers built outside the logging module (ConsoleHandler writes to System.err)", use = "build handlers in the logging module only" },
 { id = "java.syslog", ch = "syslog", sym = "{org.apache.logging.log4j.core.appender.SyslogAppender,ch.qos.logback.classic.net.SyslogAppender,net.logstash.*}", form = "type", via = ["import-alias"], why = "system log appenders created in code", use = "configure in logging module" },
 { id = "java.system-logger", ch = "stderr", sym = "java.lang.System.getLogger, System.Logger.log", form = "method", via = ["import-alias", "attr-chain"], why = "the facade itself; allowed, listed so the resolver can classify it as sanctioned", use = "sanctioned", sev = "advisory" },
 { id = "java.jni", ch = "ffi", sym = "native methods, java.lang.foreign.{Linker.downcallHandle,SymbolLookup.libraryLookup}, com.sun.jna.Native.load", form = "ffi", via = ["extern-decl", "import-alias"], why = "calls libc printf, write, puts", use = "logger" },
 { id = "java.jul-bridge", ch = "debugger", sym = "android.util.Log.{v,d,i,w,e,wtf,println}", form = "method", via = ["import-alias", "attr-chain"], why = "Android logcat", use = "SLF4J android binding in the logging module" },
]
```

### 4.6 Zig (planned)

```toml output-atoms
language = "zig"
atoms = [
 { id = "zig.debug-print", ch = "stderr", sym = "std.debug.print", form = "fn", via = ["assign-alias", "attr-chain", "reexport"], why = "formats to stderr under a global lock", use = "std.log.info/warn/err" },
 { id = "zig.debug-lock", ch = "stderr", sym = "std.debug.{lockStdErr,unlockStdErr,getStderrMutex,dumpCurrentStackTrace,dumpStackTrace,dumpHex,panic,panicExtra}", form = "fn", via = ["assign-alias", "attr-chain"], why = "stderr access and stack traces", use = "std.log.err" },
 { id = "zig.panic", ch = "implicit", sym = "@panic, std.debug.panic, unreachable, std.debug.assert failure", form = "fn", via = [], why = "the panic handler prints the message and trace to stderr", use = "return an error and log it; custom panic handler that calls std.log", sev = "advisory" },
 { id = "zig.getstd", ch = "stdout", sym = "std.io.getStdOut | std.fs.File.stdout | std.io.getStdErr | std.fs.File.stderr | std.io.getStdIn", form = "fn", via = ["assign-alias", "attr-chain", "handle-flow", "reexport"], why = "std handles; writer(), writeAll, print, writeByte, writeFile and BufferedWriter over them are outputs (stdout and stderr by name)", use = "std.log" },
 { id = "zig.bufwriter", ch = "stream", sym = "std.io.{bufferedWriter,BufferedWriter,AnyWriter,GenericWriter,Writer.Allocating}", form = "fn", via = ["assign-alias", "attr-chain", "handle-flow"], why = "buffering wrappers over a std handle or file", use = "std.log", when = "inner writer resolves to a std handle or file" },
 { id = "zig.posix-write", ch = "fd", sym = "std.posix.{write,writev,pwrite,send,sendfile}, std.os.write, std.os.linux.write, std.os.windows.WriteFile, std.c.write", form = "fn", via = ["assign-alias", "attr-chain", "fd-literal"], why = "raw descriptor writes", use = "std.log", when = "fd is 1, 2, STDOUT_FILENO or STDERR_FILENO" },
 { id = "zig.fs-write", ch = "file", sym = "std.fs.Dir.{createFile,writeFile,openFile,atomicFile,makeOpenPath}, std.fs.cwd().{createFile,writeFile}, std.fs.createFileAbsolute, std.fs.File.{write,writeAll,pwrite}", form = "fn", via = ["assign-alias", "attr-chain", "handle-flow"], why = "files by path or handle", use = "std.log with a file-writing logFn in one module" },
 { id = "zig.path-std", ch = "fd", sym = "std.fs.*", form = "fn", via = ["path-literal"], why = "/dev/stdout, /dev/stderr, /dev/fd/1, /proc/self/fd/1", use = "std.log", when = "path resolves to a std stream path" },
 { id = "zig.child", ch = "shell", sym = "std.process.Child{.stdout_behavior=.Inherit,.stderr_behavior=.Inherit}.{spawn,spawnAndWait,run}, std.process.execv, std.process.execve", form = "fn", via = ["assign-alias", "attr-chain", "handle-flow"], why = "Inherit (the default for spawnAndWait) wires the child to our streams", use = ".Pipe and log" },
 { id = "zig.c-import", ch = "ffi", sym = "@cImport/@cInclude of stdio.h, unistd.h, syslog.h; std.c.{printf,puts,fputs,fwrite,write,syslog}", form = "ffi", via = ["extern-decl", "attr-chain"], why = "C stdio and syscalls", use = "std.log" },
 { id = "zig.extern", ch = "ffi", sym = "extern fn printf | puts | write | syslog | OutputDebugStringA", form = "ffi", via = ["extern-decl"], why = "program-declared foreign output", use = "std.log" },
 { id = "zig.progress", ch = "stderr", sym = "std.Progress.{start,Node}", form = "fn", via = ["assign-alias", "attr-chain"], why = "terminal progress UI written to stderr", use = "CLI presentation module", sev = "advisory" },
 { id = "zig.log-options", ch = "stderr", sym = "std.options.logFn, std.log.defaultLog", form = "fn", via = ["attr-chain", "assign-alias"], why = "the default logFn writes to stderr; overriding or calling it directly outside the logging module is a sink choice", use = "define std_options.logFn in one module", sev = "advisory" },
 { id = "zig.windows-debug", ch = "debugger", sym = "std.os.windows.kernel32.OutputDebugStringA", form = "ffi", via = ["attr-chain", "extern-decl"], why = "debugger channel", use = "std.log" },
]
```

### 4.7 C, C++ and CUDA (planned)

Notes. Macros make detection harder: `#define say(...) printf(__VA_ARGS__)`
is `macro-wrap`, and tree-sitter-c parses the macro body as preprocessor
text, so the resolver re-parses `#define` replacement lists as expressions
and records the wrapped symbol. `stdout` and `stderr` are `FILE *`
lvalues; `fprintf(stderr, ..)` is an atom through its first argument.

```toml output-atoms
language = "c"
atoms = [
 { id = "c.stdio-out", ch = "stdout", sym = "printf,vprintf,puts,putchar,putc_unlocked,putchar_unlocked,printf_s,wprintf,putwchar,fputws,wprintf", form = "fn", via = ["macro-wrap", "assign-alias"], why = "C stdio output to stdout", use = "LOG_INFO macro over the project sink" },
 { id = "c.stdio-stream", ch = "stream", sym = "fprintf,vfprintf,fputs,fputc,putc,fwrite,fputws,fputwc,fflush,setvbuf,freopen,fdopen,fwrite_unlocked,dprintf,vdprintf", form = "fn", via = ["macro-wrap", "assign-alias", "handle-flow"], why = "writes to the FILE or fd argument; an output when it is stdout, stderr or a file", use = "LOG_* macro", when = "stream argument is stdout, stderr or any FILE*" },
 { id = "c.stderr-helpers", ch = "stderr", sym = "perror,psignal,err,errx,warn,warnx,verr,verrx,vwarn,vwarnx,error,error_at_line,assert,__assert_fail,abort", form = "fn", via = ["macro-wrap"], why = "diagnostic helpers that write to stderr", use = "LOG_ERROR macro" },
 { id = "c.fd-write", ch = "fd", sym = "write,writev,pwrite,pwritev,sendfile,send,sendto,splice,tee,copy_file_range", form = "fn", via = ["macro-wrap", "fd-literal", "assign-alias"], why = "raw descriptor writes", use = "LOG_* macro", when = "fd is 1, 2, STDOUT_FILENO or STDERR_FILENO" },
 { id = "c.file-open", ch = "file", sym = "fopen,fopen_s,freopen,open,openat,creat,mkstemp,tmpfile,fdopen", form = "fn", via = ["macro-wrap", "path-literal"], why = "opens a file for write or append; /dev/stdout, /dev/stderr, /dev/fd/N, /proc/self/fd/N and /dev/tty name std streams", use = "the logging library's file sink" },
 { id = "c.syslog", ch = "syslog", sym = "syslog,vsyslog,openlog,closelog,setlogmask,sd_journal_print,sd_journal_send,sd_journal_printv,sd_journal_stream_fd,sd_journal_sendv", form = "fn", via = ["macro-wrap", "assign-alias"], why = "system log", use = "wrap in the project sink, called from one module" },
 { id = "c.android", ch = "syslog", sym = "__android_log_print,__android_log_write,__android_log_vprint,__android_log_assert,android logcat macros", form = "fn", via = ["macro-wrap"], why = "Android logcat", use = "project sink" },
 { id = "c.win", ch = "debugger", sym = "OutputDebugStringA,OutputDebugStringW,WriteConsoleA,WriteConsoleW,WriteFile,ReportEventA,ReportEventW,DbgPrint,DbgPrintEx,_CrtDbgReport,_RPT0,_RPTF0", form = "fn", via = ["macro-wrap", "assign-alias"], why = "debugger and console writers on Windows", use = "project sink" },
 { id = "c.process", ch = "shell", sym = "system,popen,pclose,execl,execlp,execle,execv,execvp,execve,posix_spawn,posix_spawnp,fork+exec,CreateProcess", form = "fn", via = ["macro-wrap"], why = "child stdio inherited", use = "pipe the child and log" },
 { id = "c.cpp-streams", ch = "stdout", sym = "std::cout,std::cerr,std::clog,std::wcout,std::wcerr,std::wclog,std::ostream::{write,put,flush},std::print,std::println,std::osyncstream", form = "attr", via = ["import-alias", "glob-import", "assign-alias", "handle-flow"], why = "C++ iostream and C++23 print on std streams", use = "spdlog/glog sink in the logging module" },
 { id = "c.cpp-fs", ch = "file", sym = "std::ofstream,std::fstream,std::filebuf,std::ostringstream+write to file,std::filesystem::copy", form = "type", via = ["import-alias", "glob-import", "handle-flow"], why = "file writers", use = "logging library file sink" },
 { id = "c.glog", ch = "stderr", sym = "glog,spdlog,log4cxx,boost::log,Poco::Logger,g3log,zlog,easylogging++ sinks constructed outside the logging module", form = "fn", via = ["import-alias", "glob-import", "macro-wrap"], why = "logging libraries are sanctioned only when configured in the logging module", use = "configure once", sev = "advisory" },
 { id = "c.cuda-printf", ch = "stdout", sym = "printf (device), cudaPrintf, cudaDeviceSetLimit(cudaLimitPrintfFifoSize), assert (device), __trap", form = "fn", via = ["macro-wrap"], why = "device printf is flushed to host stdout at synchronization points; there is no device logging facade", use = "write to a device buffer and log on the host", sev = "advisory" },
 { id = "c.dlsym", ch = "ffi", sym = "dlopen+dlsym of any of the above", form = "ffi", via = ["extern-decl", "handle-flow"], why = "late-bound output functions", use = "project sink", sev = "advisory" },
]
```

### 4.8 Bash (planned)

Notes. In a shell every external command is an output, so only the
shell's own writers and redirections are atoms. The grammar models
redirections (`file_redirect`, `heredoc_redirect`, `herestring_redirect`)
as nodes, which makes `>&2` and `>file` symbolic, and `command_name`
nodes give builtin names, so a function or variable named `echo` is
resolved before matching (shadowing by `function echo()` is honoured).

```toml output-atoms
language = "bash"
atoms = [
 { id = "sh.echo", ch = "stdout", sym = "echo", form = "cmd", via = ["assign-alias", "bind-call"], why = "writes its arguments to stdout", use = "log info" },
 { id = "sh.printf", ch = "stdout", sym = "printf", form = "cmd", via = ["assign-alias", "bind-call"], why = "formatted write to stdout (printf -v writes to a variable and is not an output)", use = "log info", when = "no -v option" },
 { id = "sh.cat-tee", ch = "stdout", sym = "cat,tee,tac,yes,head,tail,column,fmt,pr,od,hexdump,xxd,paste,nl,rev,sort,uniq,seq,jq,wall,write", form = "cmd", via = ["assign-alias", "bind-call"], why = "filters write to stdout unless captured or redirected; tee also writes files", use = "capture the output and log it", sev = "advisory" },
 { id = "sh.dumpers", ch = "stdout", sym = "declare -p,typeset -p,set,env,printenv,export -p,readonly -p,alias,type,help,times,dirs,pwd,history,jobs,umask,ulimit -a,trap -p,caller,compgen,shopt,getopts(OPTERR),bind -p,hash -l", form = "cmd", via = ["bind-call"], why = "builtins that dump state to stdout", use = "capture and log", sev = "advisory" },
 { id = "sh.read-prompt", ch = "stderr", sym = "read -p,select,PS3,PS1,PS2", form = "cmd", via = ["bind-call"], why = "prompts go to stderr", use = "a prompt helper in a CLI module", sev = "advisory" },
 { id = "sh.stderr-redirect", ch = "stderr", sym = ">&2,1>&2,>/dev/stderr,2>&1,&>,>&,|&", form = "redirect", via = ["redirect-target", "path-literal", "fd-literal"], why = "rewires an output to stderr or merges streams", use = "log error" },
 { id = "sh.stdout-redirect", ch = "stdout", sym = ">&1,2>&1 target,>/dev/stdout,>/dev/fd/1,>/proc/self/fd/1,>/dev/tty,>/dev/console", form = "redirect", via = ["redirect-target", "path-literal", "fd-literal"], why = "names a std stream explicitly", use = "log info" },
 { id = "sh.file-redirect", ch = "file", sym = ">file,>>file,>|file,<>file,&>file,&>>file,N>file,tee file,dd of=file,install,cp,mv,sponge", form = "redirect", via = ["redirect-target", "path-literal"], why = "writes a file", use = "log function writing to the one configured fd" },
 { id = "sh.exec-redirect", ch = "implicit", sym = "exec >file,exec 2>file,exec N>file,exec >&N,exec {fd}>file", form = "redirect", via = ["redirect-target"], why = "rewires the shell's own std fds for the rest of the script", use = "configure once at the top of the entry script only", sev = "advisory" },
 { id = "sh.procsub", ch = "stream", sym = "> >(cmd), >(cmd), <(cmd)", form = "redirect", via = ["redirect-target"], why = "process substitution routes output through another command", use = "log function", sev = "advisory" },
 { id = "sh.xtrace", ch = "stderr", sym = "set -x,set -v,set -o xtrace,set -o verbose,PS4,BASH_XTRACEFD,bash -x,trap DEBUG", form = "cmd", via = ["bind-call"], why = "traces every command to stderr or BASH_XTRACEFD", use = "debug logging gated by a log level", sev = "advisory" },
 { id = "sh.syslog", ch = "syslog", sym = "logger,systemd-cat,systemd-notify,journalctl --,notify-send,mail,mailx,curl+POST to a collector", form = "cmd", via = ["assign-alias", "bind-call"], why = "writes to the system log or elsewhere; logger(1) is the sanctioned replacement when called from the single log function", use = "logger inside the log() function only" },
 { id = "sh.fd-write", ch = "fd", sym = "echo >&N,printf >&N,exec 3>&1,/dev/fd/N,/proc/self/fd/N,>&$LOGFD", form = "redirect", via = ["redirect-target", "fd-literal"], why = "writes to a numbered descriptor; N of 1 or 2 is a std stream", use = "log function", when = "N is 1 or 2" },
 { id = "sh.pager", ch = "stdout", sym = "less,more,most,bat,watch,script,screen,tmux", form = "cmd", via = ["assign-alias"], why = "terminal programs that write to the tty", use = "none in scripts", sev = "advisory" },
 { id = "sh.eval", ch = "stdout", sym = "eval,source,.,$(...),`...`", form = "cmd", via = ["bind-call"], why = "text-built commands can reach any atom; reported as unresolved-dynamic", use = "avoid", sev = "advisory" },
 { id = "sh.die", ch = "stderr", sym = "die,warn,fatal,error,log_error user-defined functions that wrap echo >&2", form = "cmd", via = ["assign-alias"], why = "wrapper functions are atoms by transitivity: a function whose body reaches an atom is itself an atom outside the logging module", use = "the single log() function" },
]
```

## 5. Cross-cutting rules for the resolver

1. Transitive wrappers. A function whose body calls an atom becomes an
   atom itself for callers outside the logging module (`re-export` and
   `macro-wrap` are the one-hop cases; the call graph handles the rest).
   The logging module is the allow-listed boundary; calls inside it are
   never reported.
2. Argument conditions. Atoms with `when` match only when the argument
   constant-folds (or flows through `handle-flow`/`fd-literal`) to the
   named condition; if the argument cannot be resolved the finding is
   `unresolved-dynamic`, reported advisory, not silent.
3. Shadowing. A binding in an enclosing scope (parameter, local,
   `def print`, `let console`) removes the atom for that scope;
   scopes follow the language grammar, not indentation.
4. Strings and comments are never searched; docstrings and test fixtures
   are plain string nodes.
5. Tests and build scripts. `#[cfg(test)]`, `tests/`, `build.rs`, `__main__`
   guards and CLI entry points are exempted by the rule's path
   configuration, not by this catalogue.
6. `sev = "advisory"` atoms are reported at warn level by default and can
   be promoted per project; every other atom is a waivable error
   (`frob:waive` with a reason).

## 6. Coverage against ~JKKJPTT

| ~JKKJPTT criterion | Where |
|---|---|
| 1 direct calls: Rust macros, Python `print`, JS `console.*`, C# `Console.Write*` | `rust.print*`, `py.print`, `js.console-*`, `cs.console-write` |
| 4 Python list (print, sys streams, writelines, flush, `__stdout__`, `os.write`, `os.fdopen`, `/dev/stdout`, subprocess, traceback, pprint, warnings, handlers, redirect_stdout) | `py.print`, `py.sys-*`, `py.os-*`, `py.path-std`, `py.subprocess`, `py.traceback`, `py.pprint`, `py.warnings`, `py.logging-*`, `py.redirect` |
| 5 symbolic detection with alias and re-export fixtures | section 3 classes, each atom's `via` |
| 6 catalogue read by the rule | section 2 blocks |

## 7. Open points

- Method receivers on user types (a field of type `Stdout` passed through
  several structs) need type inference; the first release resolves one
  hop of `handle-flow` and reports the rest as `unresolved-dynamic`.
- Languages beyond the table (Kotlin, Go, Swift, Ruby, PHP) are out of
  scope until grimble supports them; the schema needs no change to add
  them.
- Third-party printers (`rich`, `chalk`, `click`) are listed advisory
  because their set is open-ended; projects extend the table by adding
  rows in a local override block of the same shape.

## Implementation status (LOG001 and LOG002)

The `grimble-check` rules LOG001 and LOG002 read this catalogue at build
time (`include_str!`), so a new row needs no code change. Known gaps,
each tracked as a follow-up ticket:

- Atoms with `sev = "advisory"` are loaded but not reported, because
  `gob_rules::Severity` has only Unresolved and Error.
- Atoms whose `when` is a data-flow condition (not an fd or path
  literal) are skipped; `handle-flow` is not tracked past one binding.
- A `mode_arg` that is not a string literal is skipped, not flagged.
- Rust `macro_rules!` expansion and `extern "C"` FFI atoms are not
  resolved.
- Planned languages (Java, Zig, C/C++/CUDA, Bash) have no scanner yet.
- Dynamic JavaScript targets such as `console[name]` are not yet
  reported as Unresolved.
