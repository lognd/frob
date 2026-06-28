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

from frob._frob_state import ensure_gitignore


class TodoError(ErrorSet):
    NotFound = "TODO item not found"
    InvalidId = "Item ID must be a positive integer"


_TODO_FILE = ".frob/todo.md"
_ITEM_RE = re.compile(r"^- \[(?P<done>[ x])\] \[#(?P<id>\d+)\] (?P<text>.+)$")
_COUNTER_RE = re.compile(r"^<!-- next_id: (\d+) -->$")


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


def _load(project_root: Path) -> tuple[list[TodoItem], int]:
    """Returns (items, max_id_seen)."""
    p = _todo_path(project_root)
    if not p.exists():
        return [], 0
    items: list[TodoItem] = []
    max_id = 0
    for line in p.read_text().splitlines():
        cm = _COUNTER_RE.match(line.strip())
        if cm:
            max_id = int(cm.group(1))
            continue
        m = _ITEM_RE.match(line.strip())
        if m:
            item_id = int(m.group("id"))
            items.append(
                TodoItem(
                    item_id=item_id,
                    done=m.group("done") == "x",
                    text=m.group("text"),
                )
            )
            if item_id > max_id:
                max_id = item_id
    return items, max_id


def _save(project_root: Path, items: list[TodoItem], max_id: int) -> None:
    p = _todo_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# frob todo", f"<!-- next_id: {max_id} -->", ""]
    for item in items:
        mark = "x" if item.done else " "
        lines.append(f"- [{mark}] [#{item.item_id}] {item.text}")
    p.write_text("\n".join(lines) + "\n")
    ensure_gitignore(project_root)


def _next_id(max_id: int) -> int:
    return max_id + 1


def add_todo(text: str, *, project_root: Path) -> TodoItem:
    items, max_id = _load(project_root)
    new_id = _next_id(max_id)
    item = TodoItem(
        item_id=new_id,
        text=text,
        done=False,
        added_at=time.strftime("%Y-%m-%d"),
    )
    items.append(item)
    _save(project_root, items, new_id)
    return item


def done_todo(item_id: int, *, project_root: Path) -> Result[TodoItem, TodoError]:
    items, max_id = _load(project_root)
    for item in items:
        if item.item_id == item_id:
            item.done = True
            _save(project_root, items, max_id)
            return Ok(item)
    return Err(TodoError.NotFound)


def remove_todo(item_id: int, *, project_root: Path) -> Result[None, TodoError]:
    items, max_id = _load(project_root)
    new_items = [i for i in items if i.item_id != item_id]
    if len(new_items) == len(items):
        return Err(TodoError.NotFound)
    _save(project_root, new_items, max_id)
    return Ok(None)


def list_todos(project_root: Path, *, show_done: bool = False) -> TodoList:
    items, _ = _load(project_root)
    if not show_done:
        items = [i for i in items if not i.done]
    return TodoList(items=items)


def clear_done(project_root: Path) -> int:
    items, max_id = _load(project_root)
    before = len(items)
    items = [i for i in items if not i.done]
    _save(project_root, items, max_id)
    return before - len(items)
