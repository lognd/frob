from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.todo import add_todo, clear_done, done_todo, list_todos, remove_todo


def run(cfg: AppConfig) -> None:
    root = Path(".").resolve()

    match cfg.todo_command:
        case "add":
            if not cfg.todo_text:
                print("todo add: text required", file=sys.stderr)
                sys.exit(1)
            item = add_todo(cfg.todo_text, project_root=root)
            print(f"added #{item.item_id}: {item.text}")

        case "done":
            if cfg.todo_id is None:
                print("todo done: id required", file=sys.stderr)
                sys.exit(1)
            result = done_todo(cfg.todo_id, project_root=root)
            if result.is_err:
                print(f"error: {result.danger_err.value}", file=sys.stderr)
                sys.exit(1)
            item = result.danger_ok
            print(f"done #{item.item_id}: {item.text}")

        case "remove":
            if cfg.todo_id is None:
                print("todo remove: id required", file=sys.stderr)
                sys.exit(1)
            result = remove_todo(cfg.todo_id, project_root=root)
            if result.is_err:
                print(f"error: {result.danger_err.value}", file=sys.stderr)
                sys.exit(1)
            print(f"removed #{cfg.todo_id}")

        case "clear-done":
            removed = clear_done(root)
            print(f"removed {removed} completed item{'s' if removed != 1 else ''}")

        case "list" | None:
            todos = list_todos(root, show_done=cfg.todo_all)
            print(todos.as_text())

        case _:
            print("usage: frob todo <add|done|remove|list|clear-done> ...", file=sys.stderr)
            sys.exit(1)
