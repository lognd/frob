Ledger writes now wait for a held .git/index.lock for a time scaled by [git] cas_retries (2 s per attempt) instead of a fixed 10 s, and log when the budget is spent.
