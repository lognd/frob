+++
id = "01M5XMR67K19SFAWNTDJKKJPTT"
title = "Grimble rule: all output goes through a logging crate (stdout, stderr and file sinks), per language"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M5XMN7Z3TWMW8YMGVE2QBC17"
reporter = "lognd"
created = "2026-10-27T02:59:07Z"
updated = "2026-10-27T03:01:37Z"
scope = ["crates/grimble-check/**", "crates/grimble-capabilities/**"]

[[acceptance]]
text = "a grimble rule reports direct output calls (Rust println!/eprintln!/print!/dbg!, Python print, JS console.*, C# Console.Write*) outside a configured logging module, as a waivable error with a required reason"
bound = false

[[acceptance]]
text = "the rule requires that a program that emits output (stdout, stderr or files) has a logging crate configured; the sink may be file, stdout or stderr but must be reached through the logging layer"
bound = false

[[acceptance]]
text = "the finding message tells agents to obey and humans how to waive with frob:waive"
bound = false

[[acceptance]]
text = "Python coverage includes print, sys.stdout/sys.stderr write, writelines and flush, sys.__stdout__/__stderr__, os.write on fd 1 and 2, os.fdopen/open of /dev/stdout, subprocess inheriting stdio, traceback.print_*, pprint, warnings.warn and warnings.showwarning, logging.StreamHandler or FileHandler built outside the configured logging module, and contextlib.redirect_stdout targets"
bound = false

[[acceptance]]
text = 'detection is symbolic, never a lexical needle: calls are matched on parsed syntax trees with import and alias resolution (import sys as s; from sys import stdout as o; p = print; getattr(sys, "stdout"); builtins.print; a re-exported wrapper) so renames and aliases are caught and a local variable merely named print or a string or comment containing it is not; each supported language has fixtures for aliased, re-exported and negative (shadowed, string, comment) cases'
bound = false

[[acceptance]]
text = "an exhaustive per-language catalogue of output atoms (stdout, stderr, file, fd, syslog, debugger, FFI/libc, shell-out) is committed as data under docs/ with one row per atom, language, symbol path and the reason it counts, and the rule reads that catalogue so adding an atom needs no code change"
bound = false
+++

Owner request 2026-10-26: every sink must route through a logging crate; grimble should enforce it for all supported languages. Complements the frob-side clippy ban.
