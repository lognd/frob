"""T-3922: none of frob's third-party GitHub Actions were SHA-pinned --
every `uses:` was a mutable tag or branch, including the action that
publishes to PyPI with the OIDC trusted-publishing credential. Locks
that every `uses:` in .github/workflows/*.yml is a 40-hex commit SHA.
"""

import re
from pathlib import Path

import yaml

_WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"
_SHA_PIN_RE = re.compile(r"^[0-9a-f]{40}$")


def _uses_refs(workflow_path: Path) -> list[str]:
    """Every raw `uses:` value in `workflow_path`, read as text (not
    parsed YAML) so a malformed or mutated ref still shows up literally,
    the same shape a real `git diff` would surface it in."""
    text = workflow_path.read_text(encoding="utf-8")
    return re.findall(r"^\s*uses:\s*(\S+)", text, flags=re.MULTILINE)


class TestGitHubActionsArePinnedToShas:
    """T-3922: a moved tag or branch in a third-party action is arbitrary
    code running with this repo's publishing identity or build toolchain
    -- every `uses:` ref must be a 40-hex commit SHA, not a mutable tag
    or branch name."""

    def test_ci_workflow_uses_are_all_sha_pinned(self) -> None:
        # frob:tests .github/workflows/ci.yml
        refs = _uses_refs(_WORKFLOWS_DIR / "ci.yml")
        assert refs, "expected at least one uses: line in ci.yml"
        unpinned = [ref for ref in refs if "@" not in ref or not _SHA_PIN_RE.match(ref.split("@", 1)[1])]
        assert not unpinned, (
            f"ci.yml has mutable (non-SHA-pinned) action ref(s): {unpinned!r} "
            "-- pin to a 40-hex commit SHA with a trailing version comment"
        )

    def test_release_workflow_uses_are_all_sha_pinned(self) -> None:
        # frob:tests .github/workflows/release.yml
        refs = _uses_refs(_WORKFLOWS_DIR / "release.yml")
        assert refs, "expected at least one uses: line in release.yml"
        unpinned = [ref for ref in refs if "@" not in ref or not _SHA_PIN_RE.match(ref.split("@", 1)[1])]
        assert not unpinned, (
            f"release.yml has mutable (non-SHA-pinned) action ref(s): "
            f"{unpinned!r} -- pin to a 40-hex commit SHA with a trailing "
            "version comment. This is the workflow that publishes to PyPI "
            "under OIDC trusted publishing; a moved branch/tag here is "
            "arbitrary code running with the publish credential."
        )

    def test_release_workflow_yaml_still_parses(self) -> None:
        # frob:tests .github/workflows/release.yml
        text = (_WORKFLOWS_DIR / "release.yml").read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        assert parsed["jobs"], "release.yml must still parse into a normal jobs mapping"

    def test_ci_workflow_yaml_still_parses(self) -> None:
        # frob:tests .github/workflows/ci.yml
        text = (_WORKFLOWS_DIR / "ci.yml").read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        assert parsed["jobs"], "ci.yml must still parse into a normal jobs mapping"
