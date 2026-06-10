# frob init

Scaffold new projects from registered templates.

## Usage

```
frob init list
frob init new <type> <name> [--output <dir>]
```

## Commands

### `list`

Prints all registered project types and their file manifests.

### `new <type> <name>`

Renders the template manifest for `<type>`, writing files into `./<name>/`
(or `--output <dir>/<name>/`). Skips existing files unless `--force` is passed.

Template variables available in every `.j2` file:

| Variable | Value |
|----------|-------|
| `project.name` | the `<name>` argument |
| `project.type` | the `<type>` argument |

## Templates

Template files live in `src/frob/init/data/`. File naming convention:

```
pyproject.toml.j2                   -- shared across types
python_tool.__main__.py.j2          -- only rendered for python-tool
```

The type prefix (everything before the first `.`) is stripped when the file is
written. Paths in the manifest may themselves be Jinja2 expressions:

```python
Path("src/{{ project.name }}/__init__.py")
```

## Error Handling

Renderer returns `Result[list[Path], InitError]`:

- `InitError.TemplateNotFound` -- `.j2` source missing from data dir
- `InitError.OutputExists` -- target already exists (pass `--force` to overwrite)
- `InitError.RenderFailed` -- Jinja2 raised an error
- `InitError.UnknownType` -- requested project type not in manifest registry
