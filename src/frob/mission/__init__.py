"""
frob mission -- structured subagent dispatch via temporary markdown briefings.

Workflow:
  1. Orchestrator: frob mission new fix src/file.py fn -> .frob/missions/<id>.md
  2. Subagent: read the .md file, do the work, call frob mission done <id> when finished
  3. If blocked: call frob mission stuck <id> "reason" -> .frob/missions/stuck/<id>.md

The mission file is the contract between the orchestrator and the subagent.
All context is pre-assembled (frob ctx output, error, instructions) so the
subagent needs zero additional tool calls to understand its task.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

_MISSIONS_DIR_NAME = ".frob/missions"
_GITIGNORE_ENTRY = ".frob/"


class MissionError(ErrorSet):
    NotFound = "Mission file not found"
    AlreadyExists = "Mission with this ID already exists"
    InvalidType = "Unknown mission type"


class MissionMeta(BaseModel):
    model_config = {}

    id: str
    type: str  # fix | test | implement | review
    file: str | None = None
    target: str | None = None
    error: str | None = None
    test_name: str | None = None
    created: str = ""


_INSTRUCTIONS: dict[str, str] = {
    "fix": """\
## Your task

Fix the specific error shown above. Read only what you need.

**Recommended workflow:**
1. The context above (from `frob ctx`) is your primary reference -- do not re-run it.
2. Use `frob edit {file} {target} --replace` to write your fix in-place.
   Pipe the new function body directly -- you do NOT need to Read the whole file.
3. Run `frob check {check_path} --skip-arch --skip-dup` to verify.
   Or run the specific failing test: `pytest {test_name} -x` if provided.

**Escape hatch:** If you cannot figure out the fix, output exactly:
```
STUCK: <one sentence explaining what is unclear or missing>
```
Then run `frob mission stuck {id} "your reason"` to mark this mission blocked.
Do NOT delete the mission file if stuck.

**When done:** Run `frob mission done {id}`
""",
    "test": """\
## Your task

Write pytest tests for the target function. Return a unified diff only.

**Recommended workflow:**
1. The context above shows the function signature and dependencies.
2. Write tests in the specified test file (create if missing, diff against /dev/null).
3. Tests must cover: happy path, each ErrorSet variant, edge cases.
4. Apply with: `patch -p1 < your.diff`
5. Verify: `pytest {test_name} -x` then `frob mission done {id}`

**Escape hatch:**
```
STUCK: <reason the function cannot be tested as-is>
```
Then `frob mission stuck {id} "reason"`
""",
    "implement": """\
## Your task

Implement the stubbed function (body is `...`). Return a unified diff only.

**Recommended workflow:**
1. Read the context above -- it has the stub and all import signatures.
2. Use `frob edit {file} {target} --replace` to write the implementation in-place.
   You do NOT need to Read the file -- the context has what you need.
3. Verify: `frob check {check_path} --skip-arch --skip-dup`
4. Then `frob mission done {id}`

**Rules:**
- Change ONLY the target function body.
- Use `Result[T, E]` for fallible returns. Never raise.
- Use pydantic BaseModel for structured data.

**Escape hatch:**
```
STUCK: <reason the function cannot be implemented as specified>
```
Then `frob mission stuck {id} "reason"`
""",
    "review": """\
## Your task

Review the context above for correctness, design issues, and missing error handling.
Output a structured report:

```
FINDING: [error|warning|suggestion] <file>:<line> -- <message>
```

One line per finding. No prose preamble. End with:
```
SUMMARY: <total findings> findings (<N error, M warning, K suggestion>)
```

Then `frob mission done {id}`
""",
}


def create_mission(
    mission_type: str,
    *,
    project_root: Path,
    file: Path | None = None,
    target: str | None = None,
    error: str | None = None,
    test_name: str | None = None,
    extra_context: str | None = None,
) -> Result[Path, MissionError]:
    if mission_type not in _INSTRUCTIONS:
        return Err(MissionError.InvalidType)

    missions_dir = project_root / _MISSIONS_DIR_NAME
    stuck_dir = missions_dir / "stuck"
    missions_dir.mkdir(parents=True, exist_ok=True)
    stuck_dir.mkdir(parents=True, exist_ok=True)

    _ensure_gitignore(project_root)

    # Generate short deterministic ID
    seed = f"{mission_type}{file}{target}{time.monotonic_ns()}"
    mission_id = hashlib.sha1(seed.encode()).hexdigest()[:8]
    mission_path = missions_dir / f"{mission_id}.md"

    if mission_path.exists():
        return Err(MissionError.AlreadyExists)

    # Pre-assemble context
    ctx_text = ""
    if file is not None and target is not None:
        ctx_text = _get_context(file, target, project_root)

    check_path = str(project_root) if project_root else "."
    test_name_str = test_name or ""

    instructions = _INSTRUCTIONS[mission_type].format(
        file=str(file) if file else "<file>",
        target=target or "<target>",
        check_path=check_path,
        test_name=test_name_str,
        id=mission_id,
    )

    created = _utcnow()
    meta = MissionMeta(
        id=mission_id,
        type=mission_type,
        file=str(file) if file else None,
        target=target,
        error=error,
        test_name=test_name,
        created=created,
    )

    content = _render_mission(meta, ctx_text, error, instructions, extra_context)
    mission_path.write_text(content, encoding="utf-8")
    return Ok(mission_path)


def done_mission(mission_id: str, project_root: Path) -> Result[None, MissionError]:
    path = _find_mission(mission_id, project_root)
    if path is None:
        return Err(MissionError.NotFound)
    path.unlink()
    return Ok(None)


def stuck_mission(
    mission_id: str, reason: str, project_root: Path
) -> Result[Path, MissionError]:
    path = _find_mission(mission_id, project_root)
    if path is None:
        return Err(MissionError.NotFound)
    stuck_path = path.parent / "stuck" / path.name
    stuck_path.parent.mkdir(parents=True, exist_ok=True)
    # Prepend STUCK header
    original = path.read_text(encoding="utf-8")
    stuck_path.write_text(f"<!-- STUCK: {reason} -->\n\n{original}", encoding="utf-8")
    path.unlink()
    return Ok(stuck_path)


def list_missions(project_root: Path) -> list[tuple[str, str]]:
    """Returns [(id, type)] for all pending missions."""
    missions_dir = project_root / _MISSIONS_DIR_NAME
    if not missions_dir.exists():
        return []
    out = []
    for p in sorted(missions_dir.glob("*.md")):
        mission_id = p.stem
        # Extract type from first header line
        text = p.read_text(encoding="utf-8")
        mtype = "unknown"
        for line in text.splitlines():
            if line.startswith("# Mission:"):
                mtype = line.split(":", 1)[1].strip().split()[0].lower()
                break
        out.append((mission_id, mtype))
    return out


def _find_mission(mission_id: str, project_root: Path) -> Path | None:
    missions_dir = project_root / _MISSIONS_DIR_NAME
    candidate = missions_dir / f"{mission_id}.md"
    return candidate if candidate.exists() else None


def _get_context(file: Path, target: str, root: Path) -> str:
    try:
        from frob.ctx import adaptive_context

        result = adaptive_context(file, target, root=root)
        if result.is_ok:
            return result.danger_ok.as_text()
    except Exception:
        pass
    # Fallback: try frob bundle
    try:
        from frob.bundle import build_bundle

        result = build_bundle(file, target)
        if result.is_ok:
            return result.danger_ok.as_text()
    except Exception:
        pass
    return f"(could not assemble context for {file}::{target})"


def _render_mission(
    meta: MissionMeta,
    ctx_text: str,
    error: str | None,
    instructions: str,
    extra_context: str | None,
) -> str:
    parts = [
        f"# Mission: {meta.type} {meta.target or ''}",
        f"<!-- id:{meta.id} type:{meta.type} created:{meta.created} -->",
        "",
        "## Context",
        "",
        ctx_text or "(no context assembled)",
        "",
    ]
    if error:
        parts += ["## Error to fix", "", f"```\n{error.strip()}\n```", ""]
    if extra_context:
        parts += ["## Additional context", "", extra_context, ""]
    parts += [instructions]
    return "\n".join(parts)


def _utcnow() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_gitignore(root: Path) -> None:
    gi = root / ".gitignore"
    try:
        if gi.exists():
            text = gi.read_text(encoding="utf-8")
            if _GITIGNORE_ENTRY not in text:
                gi.write_text(
                    text.rstrip() + f"\n{_GITIGNORE_ENTRY}\n", encoding="utf-8"
                )
        else:
            gi.write_text(f"{_GITIGNORE_ENTRY}\n", encoding="utf-8")
    except Exception:
        pass
