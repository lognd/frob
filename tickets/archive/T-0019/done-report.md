## Done report

connect() now detects a non-sqlite cache.db (probe SELECT after the
schema read fails), closes, unlinks, and recreates the file -- the cache
is derived state, so delete-and-recreate is the honest recovery. INV-003
evidence extended with the regression test.
