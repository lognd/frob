# sys export formats

<!-- frob:describes src/frob/strata/_export.py::export_k8s_netpol -->

## What it is and where it lives

<!-- frob:enumerates src/frob/app/sys_runner.py::_EXPORT_FORMATS members="k8s,seccomp,iam" -->
`frob sys export --format <fmt>` renders an elaborated `.strata` design
model into an operational artifact. The registry is two-part: the render
functions live in `src/frob/strata/_export.py` (`export_k8s_netpol`,
`export_seccomp`, `export_iam`, each `(model: KernelModel) -> str`), and
the CLI-facing dispatch table lives in `src/frob/app/sys_runner.py`:
`_EXPORT_FORMATS = ("k8s", "seccomp", "iam")` plus a local `dict` mapping
each format string to its render function, built lazily inside the export
command handler.

## Add-an-entry recipe (new export format)

1. Write `export_<fmt>(model: KernelModel) -> str` in
   `src/frob/strata/_export.py`, following the existing three: pure
   function, no I/O, one artifact stanza per relevant construct (a `Node`
   for k8s/seccomp, a `Flow` for iam).
2. Add the format string to `_EXPORT_FORMATS` in
   `src/frob/app/sys_runner.py`.
3. Add the format string -> function mapping in the same file's export
   dispatch dict (imported lazily alongside the other two, to keep
   `sys_runner`'s module-level import graph unchanged for formats not in
   use).
4. Add a `frob:doc` edge on the new function into
   `docs/commands/sys.md#frob-sys-export`.
5. Add a CLI-level test asserting `frob sys export --format <fmt>`
   produces the expected artifact shape for a small fixture model.

## Drift-locks that fire

- `sys_runner.py`'s handler fails closed with a usage error
  (`"--format must be one of %s"`) if the requested format is not in
  `_EXPORT_FORMATS` -- a format added to one table but not the other
  (e.g. a new `export_*` function with no `_EXPORT_FORMATS` entry) is
  simply unreachable from the CLI, not a build failure; there is no
  automatic drift-lock tying `_EXPORT_FORMATS` to the set of
  `export_*`-named functions in `_export.py`. This asymmetry is a real
  gap -- see the filed ticket in `docs/guides/extending/README.md`.
- **TEST00x** applies normally to the new public `export_*` function.
- **DOC001/DOC002** applies normally to the doc edge into
  `docs/commands/sys.md`.

## Worked example diff

<!-- frob:waive DOC004 reason="hypothetical future export format (terraform-sg) used to illustrate the add-an-entry recipe above -- export_terraform_sg is deliberately not-yet-added, not a stale reference to removed code; T-0436" -->

```python
# src/frob/strata/_export.py
def export_terraform_sg(model: KernelModel) -> str:
    """One AWS security-group resource per Boundary, ingress/egress rules
    derived from the Flow set crossing it."""
    ...

# src/frob/app/sys_runner.py
_EXPORT_FORMATS = ("k8s", "seccomp", "iam", "terraform-sg")
...
    from frob.strata._export import (
        export_iam, export_k8s_netpol, export_seccomp, export_terraform_sg,
    )
    _formats = {
        "k8s": export_k8s_netpol,
        "seccomp": export_seccomp,
        "iam": export_iam,
        "terraform-sg": export_terraform_sg,
    }
```

## Common mistakes

- Adding the render function but forgetting `_EXPORT_FORMATS` -- the CLI
  rejects the format with a usage error that names only the OLD list, so
  the new format silently reads as absent from a user's perspective even
  though the code compiles and any direct unit test calling
  `export_terraform_sg` directly still passes.
- Giving an export function I/O side effects (writing a file, hitting a
  network endpoint) -- every existing export function is pure
  `model -> str`; the CLI layer owns writing stdout/a file, keeping every
  render function trivially unit-testable against a hand-built
  `KernelModel` with no fixtures on disk.

## See also

- `docs/commands/sys.md` -- full `frob sys` command reference including
  `export`, `audit`, and `plan`.
