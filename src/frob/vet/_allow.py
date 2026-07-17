"""Loads `[vet]`/`[vet.allow]` from frob.toml (docs/vet.md "Declaration and gates").

MVP note: allow entries are coarse -- `name = true` or `name = ["reason", ...]`;
full per-capability declarations (`name = ["net", "env"]` meaning literal
capability tokens) are 0.2.x, once real capability scanning exists.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.logging import get_logger
from frob.vet._models import VetConfig

_log = get_logger(__name__)


def _parse_allow(allow_raw: object) -> dict[str, tuple[str, ...] | bool]:
    """Coerce a raw `[vet.allow]` table into `{name: bool | (reason, ...)}`,
    logging and dropping entries with an unsupported value shape."""
    allow: dict[str, tuple[str, ...] | bool] = {}
    if not isinstance(allow_raw, dict):
        return allow
    for name, value in allow_raw.items():
        if isinstance(value, bool):
            allow[str(name)] = value
        elif isinstance(value, list):
            allow[str(name)] = tuple(str(v) for v in value)
        else:
            _log.warning(
                "vet: [vet.allow] entry %r has unsupported value %r; ignoring",
                name,
                value,
            )
    return allow


# frob:doc docs/vet.md#public-api
def load_vet_config(root: Path) -> VetConfig:
    """Read `frob.toml`'s `[vet]` table; absent table -> `present=False`
    (advisory-only)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        _log.debug("vet: no frob.toml at %s; advisory-only mode", toml_path)
        return VetConfig(present=False)
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("vet: could not parse %s: %s", toml_path, exc)
        return VetConfig(present=False)

    vet = data.get("vet")
    if not isinstance(vet, dict):
        _log.info("vet: no [vet] section in %s; advisory-only mode", toml_path)
        return VetConfig(present=False)

    allow = _parse_allow(vet.get("allow", {}))

    cfg = VetConfig(
        present=True,
        enforce=bool(vet.get("enforce", False)),
        osv=bool(vet.get("osv", False)),
        quarantine_days=int(vet.get("quarantine_days", 14)),
        registry_base_url=vet.get("registry_base_url"),
        allow=allow,
    )
    _log.info(
        "vet: loaded [vet] config: enforce=%s osv=%s quarantine_days=%d allow=%d",
        cfg.enforce,
        cfg.osv,
        cfg.quarantine_days,
        len(cfg.allow),
    )
    return cfg


__all__ = ["load_vet_config"]
