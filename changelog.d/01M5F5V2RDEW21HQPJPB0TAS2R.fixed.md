Added an always-running `ci-required` aggregate job to CI that waits on the rust, crunk and docs-only jobs, so skipped path-filtered jobs no longer block merges.
