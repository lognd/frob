The mirror host now reports the ledger commit log through `TicketSource::commits`, so the mirror run watermark advances after a clean pass instead of staying unset.
