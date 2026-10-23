+++
id = "01M1T07J46YWBPJJ9PWR6JSX4B"
title = "Cache store in user cache home (r17, A-080)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:02Z"
aliases = ["crunk:T-0134"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/cache/store.py", "src/crunk/app/app.py", "src/crunk/scaffold/write.py", "tests/unit/test_cache.py", "tests/unit/test_app.py", "tests/unit/test_scaffold.py", "tests/system/test_e2e_55_cache_home.py", "tests/integration/test_int_09_cache.py", "tests/system/test_e2e_17_cache.py", "tests/system/conftest.py", "src/crunk/cache/__init__.py"]

[[acceptance]]
text = "given two cached check runs under a temp cache-dir override, when they complete, then the second hits with identical output, the project tree gains no entries, and the store holds the keyed subdirectory"
bound = false

[[acceptance]]
text = "given init on a fresh project, when the gitignore is written, then it carries no cache-directory line"
bound = false
+++

Implement the r17 design: cache_home resolution in the cache subsystem (env override, XDG fallback, short-hash-of-resolved-root subdirectory), shell consumes it instead of the root-relative name, scaffold stops appending the obsolete ignore line, legacy in-repo cache never read.
