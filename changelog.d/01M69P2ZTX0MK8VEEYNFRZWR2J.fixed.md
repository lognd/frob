The Windows CI rust job no longer fails restoring its cache on target/tests/target: the cache prefix is bumped and target/tests is removed before the cache is saved.
