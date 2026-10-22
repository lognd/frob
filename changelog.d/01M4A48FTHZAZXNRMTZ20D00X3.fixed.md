The TypeScript runner tests no longer skip in CI: the workflow installs node and `cargo dev ci` sets `FROB_REQUIRE_NODE_TESTS=1`, so a missing node fails the run.
