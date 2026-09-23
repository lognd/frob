"""Pure file-presence/content-sniff framework detection (docs/modules/webapp.md).

# frob:ticket T-5302

`detect_frameworks` is the one entry point every WEBSEC/COMPLY/A11Y/SEO/
WEBPERF rule short-circuits against: a Python CLI repo with no detected
web framework returns the empty `frozenset`, and every one of those gate
families treats that as "not relevant" rather than running expensive
tree-sitter walks over code that was never a web surface to begin with.
Detection is intentionally shallow -- marker files plus a substring sniff
of the nearest manifest -- because the cost of a false negative (a rule
family that never fires) is far higher here than the cost of a false
positive (a rule family that fires and finds nothing), and a shallow
check is one a repo owner can read and predict.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/webapp.md#frameworkkind
class FrameworkKind(StrEnum):
    """One recognized web/app framework family `detect_frameworks` can report.

    frob:ticket T-5302
    """

    NEXTJS = "nextjs"
    VITE = "vite"
    DJANGO = "django"
    FLASK = "flask"
    FASTAPI = "fastapi"
    RAILS = "rails"
    LARAVEL = "laravel"
    SVELTEKIT = "sveltekit"
    ASTRO = "astro"


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable
    (missing, binary, permission).

    frob:ticket T-5302
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_any(root: Path, *names: str) -> bool:
    """True if any of `names` exists directly under `root`.

    frob:ticket T-5302
    """
    return any((root / name).exists() for name in names)


def _manifest_mentions(root: Path, manifest_name: str, *needles: str) -> bool:
    """True if `root/manifest_name` exists and its text contains any of `needles`.

    frob:ticket T-5302
    """
    text = _read_text(root / manifest_name)
    if not text:
        return False
    return any(needle in text for needle in needles)


def _detect_sveltekit(root: Path) -> bool:
    """SvelteKit: a svelte.config.js/.ts naming @sveltejs/kit, or the
    config plus package.json.

    frob:ticket T-5302
    """
    if not _has_any(root, "svelte.config.js", "svelte.config.ts", "svelte.config.mjs"):
        return False
    for name in ("svelte.config.js", "svelte.config.ts", "svelte.config.mjs"):
        if "@sveltejs/kit" in _read_text(root / name):
            return True
    return _manifest_mentions(root, "package.json", "@sveltejs/kit")


def _detect_astro(root: Path) -> bool:
    """Astro: astro.config.mjs/.ts/.js present, or "astro" named in package.json.

    frob:ticket T-5302
    """
    if _has_any(root, "astro.config.mjs", "astro.config.ts", "astro.config.js"):
        return True
    return _manifest_mentions(root, "package.json", '"astro"')


def _detect_nextjs(root: Path) -> bool:
    """Next.js: next.config.{js,mjs,ts} present, or "next" named as a
    package.json dependency.

    frob:ticket T-5302
    """
    if _has_any(root, "next.config.js", "next.config.mjs", "next.config.ts"):
        return True
    return _manifest_mentions(root, "package.json", '"next"')


def _detect_vite(root: Path) -> bool:
    """Vite: vite.config.{js,ts,mjs} present, or "vite" named in package.json.

    Checked after Next/SvelteKit/Astro (which may embed vite internally) so
    a repo detected as one of those frameworks is not ALSO reported as
    bare vite.

    frob:ticket T-5302
    """
    if _has_any(root, "vite.config.js", "vite.config.ts", "vite.config.mjs"):
        return True
    return _manifest_mentions(root, "package.json", '"vite"')


def _detect_django(root: Path) -> bool:
    """Django: a manage.py invoking django, or "django" named in requirements/pyproject.

    frob:ticket T-5302
    """
    if "django" in _read_text(root / "manage.py").lower():
        return True
    if _manifest_mentions(root, "requirements.txt", "django", "Django"):
        return True
    return _manifest_mentions(root, "pyproject.toml", "django", "Django")


def _detect_flask(root: Path) -> bool:
    """Flask: "flask" named in requirements.txt/pyproject.toml.

    frob:ticket T-5302
    """
    if _manifest_mentions(root, "requirements.txt", "flask", "Flask"):
        return True
    return _manifest_mentions(root, "pyproject.toml", "flask", "Flask")


def _detect_fastapi(root: Path) -> bool:
    """FastAPI: "fastapi" named in requirements.txt/pyproject.toml.

    frob:ticket T-5302
    """
    if _manifest_mentions(root, "requirements.txt", "fastapi", "FastAPI"):
        return True
    return _manifest_mentions(root, "pyproject.toml", "fastapi", "FastAPI")


def _detect_rails(root: Path) -> bool:
    """Rails: a Gemfile naming the rails gem, or config/application.rb present.

    frob:ticket T-5302
    """
    if _manifest_mentions(root, "Gemfile", "rails"):
        return True
    return (root / "config" / "application.rb").exists()


def _detect_laravel(root: Path) -> bool:
    """Laravel: an artisan file, or composer.json naming laravel/framework.

    frob:ticket T-5302
    """
    if (root / "artisan").exists():
        return True
    return _manifest_mentions(root, "composer.json", "laravel/framework")


_DETECTORS: dict[FrameworkKind, Callable[[Path], bool]] = {
    FrameworkKind.SVELTEKIT: _detect_sveltekit,
    FrameworkKind.ASTRO: _detect_astro,
    FrameworkKind.NEXTJS: _detect_nextjs,
    FrameworkKind.DJANGO: _detect_django,
    FrameworkKind.FLASK: _detect_flask,
    FrameworkKind.FASTAPI: _detect_fastapi,
    FrameworkKind.RAILS: _detect_rails,
    FrameworkKind.LARAVEL: _detect_laravel,
    # vite last: sveltekit/astro/next may embed vite and must be checked first.
    FrameworkKind.VITE: _detect_vite,
}


# frob:doc docs/modules/webapp.md#detect_frameworks
def detect_frameworks(root: Path) -> frozenset[FrameworkKind]:
    """Sniff `root` for known web-framework markers, returning the frozenset of matches.

    A plain Python CLI repo (no matching marker) returns the empty
    frozenset, the signal every WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule uses
    to short-circuit to "not relevant" (owner directive, T-5302).

    frob:ticket T-5302
    """
    found: set[FrameworkKind] = set()
    for kind, detector in _DETECTORS.items():
        if detector(root):
            found.add(kind)
            _log.debug("detect_frameworks: %s matched at %s", kind, root)
    if not found:
        _log.debug("detect_frameworks: no framework detected at %s", root)
    return frozenset(found)
