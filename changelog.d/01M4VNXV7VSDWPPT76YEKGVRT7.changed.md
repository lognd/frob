frob: `cycle plan --apply` now writes all its picks with one `PmStore::assign_many` ledger commit instead of one commit per ticket; refusals are unchanged.
