"""Repo-metadata helpers orthogonal to `AppConfig` itself: the calibrated
`[arch]` frob.toml threshold reader and the stale-installed-binary warning.

Split out of `frob.app.config` (T-1270): both concerns read a repo's own
`frob.toml`/`pyproject.toml` files directly rather than the parsed
`AppConfig` instance, and neither is a field or a constructor of the
`AppConfig` schema -- a real seam distinct from the class itself. Re-
exported from `frob.app.config` unchanged, so every existing `from
frob.app.config import load_arch_config` (etc.) import keeps working. Pure
move, no behavior change.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

#: The calibrated arch thresholds (T-0373): `frob.arch.analyze_project`'s
#: own keyword defaults (30/12/8/4/500) are conservative fallbacks for
#: library callers with no `frob.toml` in scope; a real repo's `[arch]`
#: table -- or, absent one, these values -- is what `frob check`'s ARCH
#: stage and `frob arch` should actually enforce.
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_FUNCTION_LINES = 60
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_CLASS_METHODS = 12
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_LOCAL_IMPORTS = 8
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_NESTING_DEPTH = 4
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
ARCH_DEFAULT_MAX_FILE_LINES = 800

# T-0728: ARCH1xx SRP/cohesion thresholds (T-0616's `frob.arch._srp`
# checks), wired through the same `[arch]` frob.toml table as the five
# T-0373 knobs above. Values mirror `_srp.py`'s own module-level defaults
# (`LCOM4_MIN_METHODS`, etc.) unchanged -- no separate calibration pass has
# been run on these yet, so the calibrated-default posture here is
# "identical to the library default until disclosed otherwise", not a
# deliberately different number.
#: `check_lcom4`'s `min_methods` default (ARCH101).
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0728
ARCH_DEFAULT_LCOM4_MIN_METHODS = 6
#: `check_lcom4`'s `min_field_using_methods` default (ARCH101).
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0728
ARCH_DEFAULT_LCOM4_MIN_FIELD_USING_METHODS = 4
#: `check_god_module`'s `min_exports` default (ARCH102).
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0728
ARCH_DEFAULT_GOD_MODULE_MIN_EXPORTS = 10
#: `check_god_module`'s `min_clusters` default (ARCH102).
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0728
ARCH_DEFAULT_GOD_MODULE_MIN_CLUSTERS = 3
#: `check_mixed_concern_function`'s `min_decision_points` default (ARCH103).
# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0728
ARCH_DEFAULT_MIXED_CONCERN_MIN_DECISION_POINTS = 2


# frob:doc docs/modules/arch.md#frob-toml-arch-config
# frob:ticket T-0373
# frob:ticket T-0728
# frob:tests tests/unit/test_config.py::test_reads_override
# frob:tests tests/unit/test_config.py::test_missing_toml_defaults
# frob:tests tests/unit/test_config.py::test_missing_section_defaults
# frob:tests tests/unit/test_config.py::test_partial_override
# frob:tests tests/unit/test_config.py::test_malformed_toml_defaults
# frob:tests tests/unit/test_arch_srp.py::TestArchConfigThresholds.test_reads_srp_overrides  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestArchConfigThresholds.test_srp_defaults_without_frob_toml  # noqa: E501
def load_arch_config(root: Path) -> dict[str, int]:
    """The `[arch]` table from `root/frob.toml` (`max_function_lines`,
    `max_class_methods`, `max_local_imports`, `max_nesting_depth`,
    `max_file_lines`, and (T-0728) the five ARCH1xx SRP/cohesion knobs
    `lcom4_min_methods`, `lcom4_min_field_using_methods`,
    `god_module_min_exports`, `god_module_min_clusters`,
    `mixed_concern_min_decision_points`), defaulting every unset key to the
    calibrated values above -- the fix for T-0373: `frob.arch.analyze_
    project`'s own keyword defaults were reaching `frob check`'s ARCH gate
    unchanged, silently overriding the user's already-disclosed calibration
    decision (large-file at 500, long-function at 30) instead of honoring
    it. T-0728 extends the same mechanism to T-0616's SRP/cohesion family
    so ARCH101-103 are frob.toml-tunable the same way ARCH001 already is.

    Returns a plain kwargs dict ready to splat into `analyze_project(root,
    **load_arch_config(root))`. A missing or malformed `frob.toml` (or a
    missing `[arch]` table) is not an error -- it just means "use the
    calibrated defaults", same posture as `frob.gates._dup_config` and
    every other per-section frob.toml reader in this codebase.
    """
    defaults = {
        "max_function_lines": ARCH_DEFAULT_MAX_FUNCTION_LINES,
        "max_class_methods": ARCH_DEFAULT_MAX_CLASS_METHODS,
        "max_local_imports": ARCH_DEFAULT_MAX_LOCAL_IMPORTS,
        "max_nesting_depth": ARCH_DEFAULT_MAX_NESTING_DEPTH,
        "max_file_lines": ARCH_DEFAULT_MAX_FILE_LINES,
        "lcom4_min_methods": ARCH_DEFAULT_LCOM4_MIN_METHODS,
        "lcom4_min_field_using_methods": ARCH_DEFAULT_LCOM4_MIN_FIELD_USING_METHODS,
        "god_module_min_exports": ARCH_DEFAULT_GOD_MODULE_MIN_EXPORTS,
        "god_module_min_clusters": ARCH_DEFAULT_GOD_MODULE_MIN_CLUSTERS,
        "mixed_concern_min_decision_points": (
            ARCH_DEFAULT_MIXED_CONCERN_MIN_DECISION_POINTS
        ),
    }
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return defaults
    try:
        with toml_path.open("rb") as fh:
            arch_cfg = tomllib.load(fh).get("arch", {})
        return {
            key: int(arch_cfg.get(key, default)) for key, default in defaults.items()
        }
    except (OSError, tomllib.TOMLDecodeError, ValueError, TypeError) as exc:
        _log.warning("load_arch_config: frob.toml unreadable, using defaults: %s", exc)
        return defaults


def _declared_frob_version(repo_root: Path) -> str | None:
    """This checkout's own declared `[project] version`, or `None` when
    `repo_root` has no `pyproject.toml`, it is unparseable, or the project
    it declares is not `frob` at all -- `stale_install_warning`'s
    pyproject-read step, split out to keep that function under ARCH001's
    line threshold (T-1022)."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return None
    project = data.get("project", {})
    if project.get("name") != "frob":
        return None
    version = project.get("version")
    return version if isinstance(version, str) else None


# frob:ticket T-0358
# frob:doc docs/modules/app.md#entry-point
# frob:tests tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch  # noqa: E501
# frob:tests tests/unit/test_config.py::test_stale_install_warning_none_for_editable_checkout  # noqa: E501
# frob:tests tests/unit/test_config.py::test_stale_install_warning_none_when_versions_match  # noqa: E501
def stale_install_warning(repo_root: Path) -> str | None:
    """A loud, one-line warning string if the RUNNING `frob` package is
    installed OUTSIDE `repo_root`'s own `src/frob/` (a globally `uv tool
    install`ed binary, e.g. `~/.local/bin/frob`) while `repo_root` is a
    frob source checkout whose `pyproject.toml` declares a DIFFERENT
    version -- the stale-global-binary phantom-numbers trap (T-0358):
    an old installed gate implementation silently runs against a newer
    working tree, so gate rule ids the new tree has waived (e.g. SEC110/
    PII010 added after the installed version was built) read back as
    'unrecognized rule id' and violation counts are simply wrong.

    `None` (no warning) when: `repo_root` has no `pyproject.toml`, that
    file does not declare `[project] name = "frob"` (not this repo at
    all), the running package's own `__init__.py` resolves to exactly
    `repo_root/src/frob/__init__.py` (an editable install / `uv run frob`
    from this same checkout -- never stale), or the installed and
    declared versions already match. Deliberately a pure string-or-None
    return, not a log call itself, so callers can decide severity (stderr
    print for `main()`, `_log.warning` for `frob doctor`/`frob check`)."""
    import importlib.metadata
    import importlib.util

    repo_version = _declared_frob_version(repo_root)
    if not repo_version:
        return None

    spec = importlib.util.find_spec("frob")
    if spec is None or spec.origin is None:
        return None
    running_init = Path(spec.origin).resolve()
    local_init = (repo_root / "src" / "frob" / "__init__.py").resolve()
    if running_init == local_init:
        return None

    try:
        installed_version = importlib.metadata.version("frob")
    except importlib.metadata.PackageNotFoundError:
        return None
    except Exception as exc:  # noqa: BLE001 -- best-effort probe, never fatal
        _log.debug(
            "stale_install_warning: unresolvable metadata lookup failed: %s", exc
        )
        return None
    if installed_version == repo_version:
        return None

    return (
        f"frob: WARNING -- running installed frob {installed_version} "
        f"({running_init}) inside a checkout whose pyproject.toml "
        f"declares frob {repo_version}. Gate logic can differ between "
        f"versions and produce silently wrong results -- use "
        f"'uv run frob' or 'make check'/'make' instead of the bare "
        f"installed binary."
    )
