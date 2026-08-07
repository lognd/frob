## Done report

Changed:
- pyproject.toml: packaging>=24 added to [project].dependencies with a
  T-0152 comment (was dev-group only; frob.vet._cve imports
  packaging.version at module level, so every bare-wheel invocation
  crashed with ModuleNotFoundError).
- uv.lock: refreshed for the dependency move.
- tests/unit/test_runtime_deps.py (new): drift-lock walking src/frob's
  unguarded top-level imports via AST (module body only, so guarded/lazy
  imports are exempt) and asserting each third-party name maps to a
  declared [project] dependency; plus a pinned regression test for the
  exact packaging/vet._cve incident. Optional extras (z3 via frob[smt])
  and the local native crates are an explicit allow-list.

Evidence: the two node ids attached via frob ticket evidence; both pass.

Verification: reproduced the crash on the freshly reinstalled global
tool (uv tool install via make install-tool -> ModuleNotFoundError:
packaging on every invocation), applied the fix, reinstalled, and the
global frob now runs clean: frob sys audit reports PROVED including
self-conformance, frob --help exits 0.

Process note: coordinator hotfix -- the broken global tool blocked all
ledger operations, so this was fixed inline with ticket accounting
(filed, started, evidenced, closed in order) rather than dispatched to
an implementer; reviewed by the T-0148 sweep as a backstop.

Filed: none.
