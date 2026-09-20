## Done report

Root cause: the fake-gh integration test shadows PATH with a `#!/bin/sh`
script named bare "gh" and chmod 0o755's it -- both POSIX-only. On win32
this fails two ways: (1) a shebang script isn't executable at all, and (2)
even a .bat/.cmd variant would not be found, because Windows'
CreateProcess only appends the ".exe" extension to an extensionless
argv[0] (never the rest of PATHEXT) -- so the spawn falls through PATH to
whatever real gh.exe is installed on the machine instead of the fake.
Confirmed via winrun with a minimal .bat repro: the real gh.exe answered
instead of the fake.

Fix: skipif(win32) with a reason explaining the CreateProcess/PATHEXT gap.
Filed T-3799 (out of scope here) for the real underlying fix: resolving
argv[0] via shutil.which() in gitio.run_argv, which would let a PATH-
shadowing shim of any extension be found correctly on Windows.

Changed: tests/test_ghio.py (skipif on
  TestPreflightIntegration.test_real_subprocess_seam_against_a_fake_gh_binary)
Evidence: winrun-confirmed skip on win32; passes on Linux
  (tests/test_ghio.py, 20/20)
Filed: T-3799 (shutil.which-based PATH resolution in gitio.run_argv)
Gates: frob check --ticket T-3798 clean

### Changed
```
 tickets/T-3798/ticket.md | 15 +++++++++++++--
 1 file changed, 13 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ghio.py::TestPreflightIntegration::test_real_subprocess_seam_against_a_fake_gh_binary` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4340 warning(s), 923 waived
- error-findings: none (measured, zero errors)
