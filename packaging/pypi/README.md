# frob

The enforcement layer for agentic development, packaged as a Python wheel
that installs two native executables and no Python modules:

- `frob`: the ticket goblin (ticket queue, leases, evidence, gates).
- `grimble`: the design goblin, bundled as a preview.

```sh
uv tool install frob      # or: pipx install frob / pip install frob
frob --version
frob doctor
```

Source, docs and issue tracker: <https://github.com/lognd/frob>. The Rust crate
publishes as `frob-cli`; the binary and this wheel are named `frob`. The wheel
version is the workspace lockstep version.

## Building from source

See BUILDING.md next to this file in the repository (`packaging/pypi/`).
