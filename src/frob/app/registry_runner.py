"""CLI wiring for `frob registry audit` (T-0407): per-registry-file
disposition accounting over `docs/design/registry/*.yaml`.

Root cause this closes: pre-T-0407, "is this registry exhausted" was only
answerable by reading `frob check`'s violation list and mentally tallying
which entries were REG001/REG002/etc -- never a direct, honest count. This
command reports `frob.registry.audit_registry_file`'s per-kind counts
straight, so "X handled / Y deferred / Z out-of-scope / W UNACCOUNTED" is a
one-line answer, matching the ticket's own acceptance criterion.
"""

from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig
from frob.gates._registry_exhaustiveness import REGISTRY_FILES
from frob.logging import get_logger
from frob.registry import (
    CorpusError,
    append_entry,
    audit_registry_file,
    load_registry_dir,
)

_log = get_logger(__name__)

_CORPUS_ERROR_MESSAGES: dict[CorpusError, str] = {
    CorpusError.FileNotFound: "registry file does not exist",
    CorpusError.KeyNotFound: "entries key does not appear in that file",
    CorpusError.DuplicateId: "an entry with this id already exists",
}


def _render_audit_line(audit) -> str:  # noqa: ANN001
    """One human-readable `frob registry audit` report line for `audit`."""
    status = "EXHAUSTED" if audit.exhausted else "INCOMPLETE"
    return (
        f"{audit.path}: total={audit.total} handled={audit.handled} "
        f"deferred={audit.deferred} duplicate={audit.duplicate} "
        f"out_of_scope={audit.out_of_scope} unaccounted={audit.unaccounted} "
        f"malformed={audit.malformed} [{status}]"
    )


# frob:doc docs/guides/exhaustive-research.md#corpus-emit-mechanism-t-0429
# frob:ticket T-0429
def _run_add(cfg: AppConfig, registry_dir: Path) -> None:
    """`frob registry add`: append one new `disposition: pending` entry to
    `cfg.registry_add_file`'s `cfg.registry_add_key` list under
    `registry_dir` -- the exhaustive-researcher's only sanctioned write
    path into the universe corpus (T-0429)."""
    if cfg.registry_add_file is None or cfg.registry_add_id is None:
        _log.error("registry add: --file and --id and --name are required")
        return
    if cfg.registry_add_name is None:
        _log.error("registry add: --name is required")
        return

    target = registry_dir / cfg.registry_add_file
    result = append_entry(
        target,
        cfg.registry_add_key,
        cfg.registry_add_id,
        cfg.registry_add_name,
        source_doc=cfg.registry_add_source_doc,
    )
    if result.is_err:
        _log.error(
            "registry add: %s -- %s",
            _CORPUS_ERROR_MESSAGES[result.danger_err],
            target,
        )
        return
    _log.info(
        "registry add: appended %s to %s (%s)",
        cfg.registry_add_id,
        target,
        cfg.registry_add_key,
    )


# frob:ticket T-0563
# frob:ticket T-0429
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """`frob registry audit`: per-registry-file disposition counts under
    `cfg.registry_path` (defaults to `docs/design/registry` under cwd).
    `frob registry add` (T-0429): append a new pending entry -- the
    exhaustive-researcher's corpus-emit mechanism."""
    root = Path(".").resolve()
    registry_dir = (
        (cfg.registry_path or Path("docs/design/registry")).resolve()
        if cfg.registry_path is not None
        else root / "docs/design/registry"
    )

    if cfg.registry_command == "add":
        _run_add(cfg, registry_dir)
        return

    if not registry_dir.is_dir():
        _log.info("registry audit: %s does not exist -- nothing to audit", registry_dir)
        if cfg.registry_json:
            import json

            _log.info(json.dumps([], indent=2))
        return

    loaded = load_registry_dir(registry_dir, REGISTRY_FILES)
    audits = [
        audit_registry_file(result.danger_ok)
        for result in loaded.values()
        if result.is_ok
    ]

    if cfg.registry_json:
        import json

        _log.info(
            json.dumps(
                [a.model_dump() for a in sorted(audits, key=lambda a: a.path)],
                indent=2,
                sort_keys=True,
            )
        )
        return

    for audit in sorted(audits, key=lambda a: a.path):
        _log.info("registry audit: %s", _render_audit_line(audit))
