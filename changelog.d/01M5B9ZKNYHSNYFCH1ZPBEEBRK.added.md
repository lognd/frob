Ledger map-shard parsing treats a shard without an `issue` key as unmapped (`None`) instead of malformed; a present but invalid `issue` is still an error.
