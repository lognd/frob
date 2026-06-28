# frob tokens

Estimate the token cost of reading one or more files before actually reading
them. Uses a character-based heuristic (code: ~3.5 chars/token).

## Usage

```
frob tokens <path> [<path>...] [--sort] [--by-dir] [--detail]
```

`<path>` can be a file or directory. For directories, all source files are
counted recursively.

## Flags

| Flag | Description |
|------|-------------|
| `--sort` | Sort files by token count descending instead of path order |
| `--by-dir` | Show per-directory subtotals after the file list |
| `--detail` | Break down each file by region (imports, classes, functions) |

## Output (default)

```
src/frob/ast/python.py          ~1,240 tokens
src/frob/ast/cpp.py               ~980 tokens
src/frob/cycle/graph.py           ~380 tokens
--
total                           ~2,600 tokens
```

## Output (`--by-dir`)

```
src/frob/ast/python.py          ~1,240 tokens
src/frob/ast/cpp.py               ~980 tokens
src/frob/cycle/graph.py           ~380 tokens
--
total                           ~2,600 tokens

By directory:
  src/frob/ast/                 ~2,220 tokens
  src/frob/cycle/                 ~380 tokens
```

## Output (`--detail`)

Breaks down by region within the file (imports, classes, functions) so you can
decide whether to read a section or skip it.

```
src/frob/ast/python.py          ~1,240 tokens
  imports                           ~80 tokens
  get_imports (L32-L58)            ~180 tokens
  emit_stub (L130-L195)            ~420 tokens
  ...
```

## Why it exists

Before choosing what context to include in a subagent prompt, Claude needs to
know the cost. A file that "looks small" might be 2,000 tokens. `tokens` lets
you budget context without reading anything.

## Typical use

```
# Budget check before building a bundle
frob tokens src/frob/stub/__init__.py src/frob/ast/python.py
# -> total ~2,200 tokens  -- safe to include both

# Find the most expensive files first
frob tokens src/frob/ --sort

# See which directories dominate token cost
frob tokens src/frob/ --by-dir

# Find which functions are expensive before deciding what to stub
frob tokens src/frob/ --detail
```
