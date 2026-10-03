+++
id = "01M41RV691XZQ5W2EW821PHK3V"
title = "PATH family: absolute host paths, string path separators and paths in command lines (D86)"
type = "story"
category = "todo"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-03T20:56:13Z"
updated = "2026-10-03T20:56:13Z"
scope = ["crates/grimble-lints/**", "docs/reference/rules/PATH001.md", "docs/reference/rules/PATH002.md", "docs/reference/rules/PATH003.md", "grimble.toml"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7FYE5D1N2SY01VNVVACK"

[[acceptance]]
text = "Given the ~G5RJY40 Windows bugs as corpus cases, when the PATH rules run, then each bug fires its rule and each fixed version is quiet"
bound = false

[[acceptance]]
text = "Given a repository-relative path type used with /, when PATH002 runs, then it does not fire"
bound = false

[[acceptance]]
text = "Given a language adapter without path-conversion roles, when PATH002 runs, then it reports Unresolved, not clean"
bound = false
+++

Owner request 2026-10-03 (D86, docs/design/rules.md section 3.1, boundaries.md 2.5): the PATH host-path portability family. The / versus \ difference broke CI on every first Windows run (~G5RJY40: merge driver path, command allowlist compare, --cwd string compare, fixtures).

Rules (see rules.md 3.1 for the exact firing conditions and defaults):
- PATH001 absolute-host-path: absolute host path string literals (/home/<name>/, /Users/<name>/, /root/, /tmp/..., X:\ or X:/, UNC); exempt /, URLs, shebangs, [path] allowed (default /dev/null); Warn in non-test code, Advisory in tests.
- PATH002 string-path-separator: a path turned into a string (Rust to_str, to_string_lossy, display, as_os_str; Python str(p), os.fspath) then split, joined, concatenated, compared, trimmed or searched with a literal / or \ in the same function.
- PATH003 path-in-command-line: a path-derived string interpolated into one command-line string (format! into a shell command, sh -c, a git config value git runs, a .ps1 body) instead of passed as its own argument.

Implementation: GRL rules in the standard pack (PATH001 a pattern rule, PATH002 and PATH003 relational with def-use within one function), registered in the grimble-lints rule set, Unresolved for a language whose adapter lacks the path-conversion roles; per-language path-conversion callees come from the callee vocabulary. This repository sets PATH002 and PATH003 to Error in grimble.toml. Seed the corpus with the real bugs from ~G5RJY40 (before and after) so each rule fires on the bug and is quiet on the fix. Blocked on the GRL executor and std pack (~VNVVACK).
