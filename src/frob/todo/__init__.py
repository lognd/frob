"""
frob todo -- session-persistent TODO tracker for cross-session context.

Keeps a structured TODO file at .frob/todo.md. Agents can add, complete,
and list items without reading the full project. Items survive sessions.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result


class TodoError(ErrorSet):
    NotFound = "TODO item not found"
    InvalidId = "Item ID must be a positive integer"


_TODO_FILE = ".frob/todo.md"
_ITEM_RE = re.compile(r"^- \[(?P<done>[ x])\] \[#(?P<id>\d+)\] (?P<text>.+)$")


class TodoItem(BaseModel):
    model_config = {}

    item_id: int
    text: str
    done: bool
    added_at: str = ""


class TodoList(BaseModel):
    model_config = {}

    items: list[TodoItem]

    def as_text(self) -> str:
        if not self.items:
            return "no TODO items"
        pending = [i for i in self.items if not i.done]
        done = [i for i in self.items if i.done]
        lines: list[str] = []
        if pending:
            lines.append(f"## Pending ({len(pending)})")
            for item in pending:
                lines.append(f"  #{item.item_id}: {item.text}")
        if done:
            lines.append(f"## Done ({len(done)})")
            for item in done:
                lines.append(f"  #{item.item_id}: ~~{item.text}~~")
        return "\n".join(lines)


def _todo_path(project_root: Path) -> Path:
    return project_root / _TODO_FILE


def _load(project_root: Path) -> list[TodoItem]:
    p = _todo_path(project_root)
    if not p.exists():
        return []
    items: list[TodoItem] = []
    for line in p.read_text().splitlines():
        m = _ITEM_RE.match(line.strip())
        if m:
            items.append(TodoItem(
                item_id=int(m.group("id")),
                done=m.group("done") == "x",
                text=m.group("text"),
            ))
    return items


def _save(project_root: Path, items: list[TodoItem]) -> None:
    p = _todo_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# frob todo\n"]
    for item in items:
        mark = "x" if item.done else " "
        lines.append(f"- [{mark}] [#{item.item_id}] {item.text}")
    p.write_text("\n".join(lines) + "\n")
    _ensure_gitignore(project_root)


def _ensure_gitignore(root: Path) -> None:
    gi = root / ".gitignore"
    entry = ".frob/"
    if gi.exists():
        content = gi.read_text()
        if entry not in content:
            gi.write_text(content.rstrip() + f"\n{entry}\n")
    else:
        gi.write_text(f"{entry}\n")


def _next_id(items: list[TodoItem]) -> int:
    if not items:
        return 1
    return max(i.item_id for i in items) + 1


def add_todo(text: str, *, project_root: Path) -> TodoItem:
    items = _load(project_root)
    item = TodoItem(
        item_id=_next_id(items),
        text=text,
        done=False,
        added_at=time.strftime("%Y-%m-%d"),
    )
    items.append(item)
    _save(project_root, items)
    return item


def done_todo(item_id: int, *, project_root: Path) -> Result[TodoItem, TodoError]:
    items = _load(project_root)
    for item in items:
        if item.item_id == item_id:
            item.done = True
            _save(project_root, items)
            return Ok(item)
    return Err(TodoError.NotFound)


def remove_todo(item_id: int, *, project_root: Path) -> Result[None, TodoError]:
    items = _load(project_root)
    new_items = [i for i in items if i.item_id != item_id]
    if len(new_items) == len(items):
        return Err(TodoError.NotFound)
    _save(project_root, new_items)
    return Ok(None)


def list_todos(project_root: Path, *, show_done: bool = False) -> TodoList:
    items = _load(project_root)
    if not show_done:
        items = [i for i in items if not i.done]
    return TodoList(items=items)


def clear_done(project_root: Path) -> int:
    items = _load(project_root)
    before = len(items)
    items = [i for i in items if not i.done]
    _save(project_root, items)
    return before - len(items)
