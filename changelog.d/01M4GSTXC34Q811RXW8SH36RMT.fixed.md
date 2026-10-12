With ref_mode = branch and a detached HEAD, read-only verbs (ticket doctor, check) now read the ledger from the configured ticket ref; only writing verbs refuse with E-LEDGER-DETACHED.
