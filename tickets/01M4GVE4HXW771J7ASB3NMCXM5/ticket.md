+++
id = "01M4GVE4HXW771J7ASB3NMCXM5"
title = "Lift D87: release.yml uploads the Rust crunk wheels to PyPI 'crunk' (superseding the Python crunk 0.1.x) from 0.533.0; record the decision"
type = "chore"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T17:30:08Z"
updated = "2026-10-10T02:53:07Z"
scope = [".github/workflows/release.yml", "docs/design/README.md", "docs/guides/release.md", "changelog.d/**", "crates/frob-release/tests/products.rs", "packaging/pypi/BUILDING.md", "crates/frob-release/tests/release_workflow.rs"]

[[acceptance]]
text = "Given the release workflow, when 0.533.0 is cut, then the five crunk wheels are uploaded to PyPI with frob and grimble (the hold-back step is removed), docs/design/README.md records the owner decision superseding D87, and docs/guides/release.md notes that the PyPI crunk project needs the frob repository as a trusted publisher"
bound = true
+++

Owner 2026-10-09: publish the Rust crunk to PyPI as crunk, superseding lognd/crunk (Python, 0.1.x). Trigger: hullbreach gap 5 (frob 0.532.0's crunk sibling call fails against PyPI crunk 0.1.1).
