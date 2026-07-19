"""CLI wiring for `frob deploy` -- compile `std.host` `HostManifest` facts
into Linux/systemd install/status/uninstall bash (T-0257).

One verb today: `generate`. Loads every `.strata` design file under the
repo's design dir (same `load_design_ids`/`merge_models` pattern
`frob.app.sys_runner` already uses for `plan`/`doc`/`audit`), renders the
three scripts via `frob.deploy.generate_all`, and writes them to
`cfg.deploy_out_dir` (default `deploy/`) -- printing a dry-run diff
summary instead when `--check` is passed, so CI can verify the committed
scripts are current without mutating the tree (the same check the
DEPLOY001 drift gate performs during `frob check`, exposed here as a
standalone command for a pre-commit hook or manual verification).
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from frob.app.config import AppConfig
from frob.deploy import generate_all
from frob.logging import get_logger
from frob.strata import DEFAULT_DESIGN_DIR, KernelModel, load_design_ids
from frob.strata._sysdoc import merge_models

_log = get_logger(__name__)


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from `frob.toml`, defaulting like every other
    strata-consuming runner (`frob.app.sys_runner._design_dir` precedent;
    a two-line frob.toml read is not worth a cross-module import, per
    that module's own docstring)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("deploy generate: frob.toml unreadable: %s", exc)
        return DEFAULT_DESIGN_DIR
    return data.get("strata", {}).get("design_dir", DEFAULT_DESIGN_DIR)


def _load_model(root: Path) -> KernelModel | None:
    """Load+merge every `.strata` design file under the repo's design dir
    into one `KernelModel`, or `None` (error already logged) on any load
    failure or an empty design set."""
    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error(
                "deploy generate: %s failed to load: %s", error.path, error.error
            )
        return None
    if not ids.models:
        _log.info("deploy generate: no design models under %s/%s", root, design_dir)
        return None
    return merge_models(ids.models)


def _run_generate(cfg: AppConfig) -> None:
    """`frob deploy generate [--check] [path]`: write `install.sh`/
    `status.sh`/`uninstall.sh` to `deploy/` (or `--check` to verify the
    committed scripts already match, exit 1 on any mismatch, no writes)."""
    root = (cfg.deploy_path or Path(".")).resolve()
    model = _load_model(root)
    if model is None:
        sys.exit(1)

    rendered = generate_all(model)
    out_dir = root / (cfg.deploy_out_dir or Path("deploy"))

    if cfg.deploy_check:
        mismatched: list[str] = []
        for filename, content in sorted(rendered.items()):
            path = out_dir / filename
            if not path.exists():
                mismatched.append(filename)
                continue
            if path.read_text(encoding="utf-8") != content:
                mismatched.append(filename)
        if mismatched:
            for filename in mismatched:
                _log.error(
                    "deploy generate --check: %s missing or stale -- run "
                    "`frob deploy generate` to regenerate",
                    filename,
                )
            sys.exit(1)
        _log.info("deploy generate --check: all %d file(s) current", len(rendered))
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in sorted(rendered.items()):
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)
        _log.info("deploy generate: wrote %s", path)


# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Dispatch `frob deploy <command>`: `generate` (T-0257) is the only
    verb today."""
    if cfg.deploy_command == "generate":
        _run_generate(cfg)
        return
    _log.error("usage: frob deploy generate [--check] [path]")
    sys.exit(1)
