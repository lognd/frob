frob land now retries a git command with backoff while a concurrent ledger write holds .git/index.lock, instead of failing E-LAND-ADVANCE.
