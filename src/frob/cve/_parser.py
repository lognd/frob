"""Parser and cvelistV5 mirror walker for CVE Record Format v5 JSON
(docs/modules/cve.md is authoritative). No network anywhere: both
`parse_record` and `iter_mirror` operate purely on local paths.
"""

# frob:ticket T-0146
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError
from typani import Err, Ok
from typani.result import Result

from frob.cve._models import CveError, CveRecord
from frob.logging import get_logger

_log = get_logger(__name__)

#: cvelistV5 mirror layout: cves/YYYY/NNNxxx/CVE-YYYY-NNNN.json, where
#: NNNxxx is the CVE sequence number's thousands-bucket directory (e.g.
#: CVE-2021-44228 lives under cves/2021/44xxx/CVE-2021-44228.json).
_MIRROR_GLOB = "cves/*/*/CVE-*.json"


# frob:doc docs/modules/cve.md#public-api
def parse_record(path: Path) -> Result[CveRecord, CveError]:
    """Parse one CVE Record Format v5 JSON file at `path`.

    Unknown/extra fields are tolerated (the schema evolves); a missing
    required field or malformed JSON is a loud typed `Err`, never a
    silent partial result (vacuous-pass doctrine, docs/modules/cve.md
    "Error semantics")."""
    if not path.exists():
        _log.warning("cve: record not found: %s", path)
        return Err(CveError.NotFound)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("cve: could not read %s: %s", path, exc)
        return Err(CveError.Unreadable)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _log.warning("cve: %s is not valid JSON: %s", path, exc)
        return Err(CveError.NotJson)
    try:
        record = CveRecord.model_validate(data)
    except ValidationError as exc:
        _log.warning("cve: %s does not satisfy CVE v5 structure: %s", path, exc)
        return Err(CveError.MalformedRecord)
    _log.debug(
        "cve: parsed %s (state=%s)", record.cveMetadata.cveId, record.cveMetadata.state
    )
    return Ok(record)


# frob:doc docs/modules/cve.md#public-api
def iter_mirror(
    root: Path,
) -> Iterator[tuple[Path, Result[CveRecord, CveError]]]:
    """Walk a local cvelistV5 mirror rooted at `root`
    (`cves/YYYY/NNNxxx/CVE-YYYY-NNNN.json`), yielding `(path, result)` for
    every record file found, in sorted path order.

    Every file under the mirror layout is yielded -- a parse failure on
    one record surfaces as `Err` alongside its path rather than being
    dropped or aborting the walk (vacuous-pass doctrine: a caller that
    only looks at `Ok` results must not be able to mistake "silently
    skipped" for "clean"). If `root` itself is not a directory, yields a
    single `(root, Err(CveError.MirrorPathInvalid))` entry instead of
    raising or yielding nothing."""
    if not root.is_dir():
        _log.warning("cve: mirror root is not a directory: %s", root)
        yield (root, Err(CveError.MirrorPathInvalid))
        return
    paths = sorted(root.glob(_MIRROR_GLOB))
    _log.info("cve: walking mirror %s (%d record file(s))", root, len(paths))
    for path in paths:
        yield (path, parse_record(path))
