Board no longer re-syncs the ledger and re-walks the tickets tree for every ticket's events: it reads them all through the new `Ledger::events_many`, one sync and one walk per invocation.
