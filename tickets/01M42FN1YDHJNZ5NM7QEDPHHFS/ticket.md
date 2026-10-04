+++
id = "01M42FN1YDHJNZ5NM7QEDPHHFS"
title = 'Windows verbatim paths (\\?\) break git calls, and the GC path jail may admit a dotdot path; one canonicalize, a strict jail'
type = "security"
category = "in-progress"
priority = "critical"
points = 5
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-04T03:34:50Z"
updated = "2026-10-04T04:32:15Z"
scope = ["crates/frob-worktree/**", "crates/gob-exec/**", "crates/gob-git/**", "crates/frob-land/**", "clippy.toml", "docs/design/paths.md", "crates/gob-cache/src/lib.rs", "crates/gob-cache/Cargo.toml", "crates/gob-cache/tests/shared.rs", "crates/frob-evidence/src/provider.rs", "crates/frob-evidence/Cargo.toml", "crates/frob-tests/src/lease.rs", "crates/frob/src/init.rs", "crates/frob/Cargo.toml", "crates/frob-check/benches/full_check.rs", "crates/frob-check/Cargo.toml", "crates/gob-cache/benches/cache.rs", "Cargo.lock", "changelog.d/01M42EDPHHFS000000000000000.fixed.md", "changelog.d/01M42FN1YDHJNZ5NM7QEDPHHFS.security.md", "crates/frob-evidence/src/scrub.rs", "crates/frob/tests/merge_driver_path.rs"]

[[acceptance]]
text = "Given Windows-style verbatim, UNC and mixed-separator inputs (tested on Linux), when the jail admits a path, then no admitted path lies outside a root and any path with a dot or dotdot component is refused"
bound = false

[[acceptance]]
text = "Given the codebase, when clippy runs, then std::fs::canonicalize is disallowed outside the one canonicalization function"
bound = true

[[acceptance]]
text = "Given windows-latest CI, when the frob-worktree gc tests run, then they pass"
bound = false
+++

CI run 37173676888 (2026-10-04), windows-latest: 6 frob-worktree::gc tests fail.
(a) Five fail at git worktree add because the test fixture canonicalizes its temp dir and std::fs::canonicalize on Windows returns verbatim paths (\\?\C:\...), which git cannot use ("could not create leading directories of '//?/C:/...': Invalid argument"). Any product path that is canonicalized and handed to git or another tool breaks the same way on a real Windows machine.
(b) jail_admits_by_components_not_string_prefix_and_refuses_roots_and_dotdot fails at gc.rs:530: with a verbatim base, admitting target/debug/../../target-old does not return JailError::NotAbsolute. The GC deletes files, so find out exactly what admit returned (Ok would mean a path outside the jail could be deleted) and treat it as a security bug.

Fix structurally per paths.md (the gob-path crate is ~ARHP82G; until it exists, put the functions in one module that moves there):
1. One canonicalization function for the codebase that returns a non-verbatim path when the path can be expressed without the prefix (the dunce approach, or strip \\?\ and \\?\UNC\ where safe), used by every product call site and tests; std::fs::canonicalize is added to the clippy disallowed-methods list with that function named in the reason (paths.md section 3).
2. The jail refuses any path containing a .. or . component, in any style including verbatim, before any comparison, and compares normalized components; add property tests over Windows-style inputs (verbatim, UNC, mixed separators, case) that run on Linux with typed-path or the pure style functions already in the codebase, asserting no admitted path escapes a root.
3. Grep every canonicalize and every place a path is passed to git or gob-exec; route them through the function; list them in the report.
Until this lands, the automatic GC pass must not delete on Windows (make the pass report-only on cfg(windows)) so no Windows user can be affected.
