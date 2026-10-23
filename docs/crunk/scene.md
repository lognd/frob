# Scene ingest and layout solve

Status: current
Owner: crunk
Decisions: none

`crunk-ingest::scene` reads a JSON scene description of boxes and text runs and solves it with taffy into a layout-solve JSON. The LAYOUT and RESP rules read that solve; it does not render anything.

## Scene format

```json
{ "viewport": { "width": 320, "height": 480 },
  "root": { "id": "page", "kind": "box", "style": { "direction": "column", "padding": 16 },
            "children": [ { "id": "title", "kind": "text", "text": { "content": "Hello", "font_size": 20 } } ] } }
```

- `kind` is `box` or `text`; ids are unique strings.
- `style` keys: `display` (`flex`, `block`, `none`), `direction` (`row`, `column`), `wrap`, `gap`, `padding`, `margin`, `width`, `height` (pixels, `"auto"` or `"N%"`), `grow`, `shrink`. Unknown keys are rejected.
- `interactive` (default false) marks a pointer or touch target; LAYOUT005 sizes it and LAYOUT004 keeps it inside the safe area. A scene's top-level `safe_area` (pixels, default 0) is the inset from every viewport edge that text and targets must stay inside.
- Project scene files live at `design/scenes/*.scene.json`; the LAYOUT rules solve each one and RESP001 matches their viewport widths to `[breakpoints]`.
- A `text` node carries `text.content`, `text.font_size`, optional `line_height` (default 1.2) and `max_width`.

## HTML scene documents

- Authored scenes live at `design/scenes/**/*.scene.html`: nested directories are searched, the suffix matches in any case, and ignore files are honored. Each file is read as bytes and parsed through `crunk_scene::parse_scene_bytes`; results are ordered by project-relative path.
- A file that cannot be loaded is never a crash. SCENE005 reports it as a finding at the file: unreadable, over the 4 MiB size cap, not UTF-8, no elements (empty, blank or comments only), or a name (file name without the suffix, case-insensitive) already used by an earlier file. The loadable files are still checked by the other SCENE rules.

## Text metrics

There is no font engine, so the solve is identical everywhere: a character is `0.6 * font_size` wide, a line is `font_size * line_height` tall, and a run wraps at `max_width`.

## Layout-solve JSON

`viewport_width`, `viewport_height` and `nodes` in document order. Each node has `id`, `parent`, `kind`, absolute `x`, `y`, `width`, `height` in whole pixels, and `text` (`content`, `font_size`, `lines`) for text runs. Serialization is stable: the same scene yields byte-identical output.

## Not yet

Grid layout, per-side padding and margin, CSS-derived styles and a CLI verb are follow-up work.
