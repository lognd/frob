# PyPI packaging

One wheel set per product (D87, docs/design/products.md 6): the PyPI projects `frob` and
`grimble`, each a native executable and no Python modules.

```sh
uv tool install frob      # frob, plus grimble at the same version (a dependency)
uv tool install grimble   # grimble alone
pip install frob          # also works; both executables land in the environment
```

`frob` finds `grimble` next to its own executable, so it works even when only `frob` is on
`PATH` (as with `uv tool install`). The wheel version is the workspace lockstep version.

The product list is `products.toml`; `render.py` renders each product's maturin project from
`pyproject.template.toml` and `readme.template.md`. Source, docs and issue tracker:
<https://github.com/lognd/frob>. The Rust crate publishes as `frob-cli`; the binary and its
wheel are named `frob`.

## Building from source

See BUILDING.md next to this file in the repository (`packaging/pypi/`).
