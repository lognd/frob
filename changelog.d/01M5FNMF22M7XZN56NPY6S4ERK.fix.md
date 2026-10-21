Refresh-state cache saves now go through the shared atomic write helper instead of a hand-rolled temp-and-rename, fixing the gob-fs inventory test.
