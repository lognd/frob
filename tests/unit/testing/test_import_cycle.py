"""Regression test for T-0634: `import frob.testing` must succeed as the
first frob-touching import in a fresh interpreter, with no dependency on
`frob.gates` having been imported first (docs/modules/testing.md).
"""

from __future__ import annotations

import subprocess
import sys

# frob:ticket T-0634


def test_frob_testing_imports_standalone_in_fresh_interpreter() -> None:
    """A fresh subprocess importing only `frob.testing` must not raise
    ImportError due to the frob.testing <-> frob.gates circular import
    that used to only resolve by accident of test-collection order."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import frob.testing; print(frob.testing.CollectedTests)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "CollectedTests" in result.stdout
