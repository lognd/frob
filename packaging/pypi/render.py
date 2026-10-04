#!/usr/bin/env python3
"""Render one product's maturin project from products.toml (the single PyPI product list).

Usage:
    render.py list                       print the product names, one per line
    render.py render PRODUCT OUT_DIR     write pyproject.toml, README.md and LICENSE into OUT_DIR
    render.py version                    print the lockstep version as PEP 440

The version is the workspace lockstep version from `cargo metadata` (the frob-cli package), so a
`frob release bump` needs no edit here and a sibling pin can never drift from the wheel version.
Needs Python 3.11+ (tomllib); standard library only.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VERSION_PACKAGE = "frob-cli"
log = logging.getLogger("render")


def products() -> list[dict]:
    """The product tables of products.toml, in file order."""
    with open(HERE / "products.toml", "rb") as f:
        return tomllib.load(f)["product"]


def pep440(semver: str) -> str:
    """Convert a workspace SemVer to the PEP 440 form maturin gives the wheel."""
    m = re.fullmatch(r"(\d+\.\d+\.\d+)(?:-(alpha|beta|rc)\.?(\d+))?", semver)
    if not m:
        raise SystemExit(f"render: cannot express version {semver!r} as PEP 440")
    base, pre, n = m.groups()
    return base if pre is None else f"{base}{ {'alpha': 'a', 'beta': 'b', 'rc': 'rc'}[pre] }{n}"


def lockstep_version() -> str:
    """The version of the frob-cli package, PEP 440."""
    out = subprocess.run(
        ["cargo", "metadata", "--no-deps", "--format-version", "1", "--locked"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    for pkg in json.loads(out)["packages"]:
        if pkg["name"] == VERSION_PACKAGE:
            return pep440(pkg["version"])
    raise SystemExit(f"render: package {VERSION_PACKAGE} not found in the workspace")


def fill(template: str, fields: dict[str, str]) -> str:
    """Replace every @KEY@ in template; an unknown or unused key is a bug."""
    for key, value in fields.items():
        template = template.replace(f"@{key}@", value)
    left = re.findall(r"@[A-Z_]+@", template)
    if left:
        raise SystemExit(f"render: unfilled template fields {left}")
    return template


def render(name: str, out: Path) -> None:
    """Write the maturin project of product `name` into `out`."""
    table = next((p for p in products() if p["name"] == name), None)
    if table is None:
        raise SystemExit(f"render: unknown product {name!r}; known: {[p['name'] for p in products()]}")
    version = lockstep_version()
    out.mkdir(parents=True, exist_ok=True)
    manifest = Path(ROOT / table["manifest"])
    deps = [f"{d}=={version}" for d in table["depends"]]
    note = ""
    if deps:
        note = "Installing it also installs " + ", ".join(f"`{d}`" for d in deps) + " (same version).\n\n"
    fields = {
        "NAME": table["name"],
        "VERSION": version,
        "SUMMARY": table["summary"],
        "KEYWORDS": json.dumps(table["keywords"]),
        "DEPENDENCIES": json.dumps(deps),
        "MANIFEST": Path(os.path.relpath(manifest, out)).as_posix(),
        "DEPENDS_NOTE": note,
    }
    (out / "pyproject.toml").write_text(fill((HERE / "pyproject.template.toml").read_text(), fields))
    (out / "README.md").write_text(fill((HERE / "readme.template.md").read_text(), fields))
    shutil.copyfile(HERE / "LICENSE", out / "LICENSE")
    log.info("rendered %s %s into %s", table["name"], version, out)


def main(argv: list[str]) -> int:
    """Dispatch the three subcommands."""
    logging.basicConfig(level=logging.INFO, format="render: %(message)s", stream=sys.stderr)
    match argv:
        case ["list"]:
            print("\n".join(p["name"] for p in products()))
        case ["version"]:
            print(lockstep_version())
        case ["render", name, out]:
            render(name, Path(out).resolve())
        case _:
            print(__doc__, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
