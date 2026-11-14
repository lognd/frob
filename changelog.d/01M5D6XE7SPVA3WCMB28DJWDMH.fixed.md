`frob refresh` now exits 1 with `E-SYNC-DIVERGED` when the local base truly diverged from the remote base; bases with no shared history report `base_sync = unrelated` and stay ok.
