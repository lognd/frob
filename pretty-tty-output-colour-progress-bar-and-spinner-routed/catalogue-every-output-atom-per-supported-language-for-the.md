+++
id = "01M5XMWRV7DKX8XBBK4JXNJRTQ"
title = "Catalogue every output atom per supported language for the logging rule (research)"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M5XMN7Z3TWMW8YMGVE2QBC17"
reporter = "lognd"
created = "2026-10-27T03:01:37Z"
updated = "2026-10-27T03:01:37Z"
scope = ["docs/design/output-atoms.md"]

[[acceptance]]
text = "docs/design/output-atoms.md lists, for every language grimble supports, every way to write to stdout, stderr, files, raw fds, syslog/journald, debugger channels and by shelling out or FFI, including esoteric ones, each with its fully qualified symbol path, how it can be aliased or re-exported, and the sanctioned logging replacement"
bound = false

[[acceptance]]
text = "the catalogue is machine-readable data consumed by ~JKKJPTT, and each language row names the parser (tree-sitter grammar) and the resolution it needs (imports, aliases, attribute access, dynamic getattr) so detection is symbolic"
bound = false
+++

Owner request 2026-10-26: figure out all the ways to log in every supported language, including esoteric atoms (Python sys.stdout/stderr write and writelines, sys.__stdout__, os.write(1, ...), /dev/stdout, ctypes libc printf/write, traceback.print_exc, warnings; Rust print!/eprintln!/dbg!/std::io::stdout().write*/libc::write/Command stdio inherit; JS console.*, process.stdout.write, fs.writeSync(1, ...); C# Console.Out/Error, Debug.WriteLine, Trace, Unity Debug.Log; Java System.out/err, Logger fallbacks; Zig std.debug.print; Bash echo/printf/>&2/tee/logger; and so on). Must be derived from the language standard libraries, not guessed.
