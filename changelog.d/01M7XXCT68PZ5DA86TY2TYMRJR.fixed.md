Ledger blob reads (ticket files, events) are capped at 8 MiB and refused from the object header with `E-GIT-BLOB-TOO-LARGE`, so a hostile blob is never buffered. (~2TYMRJR)
