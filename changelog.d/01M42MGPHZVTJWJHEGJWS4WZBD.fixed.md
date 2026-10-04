frob check --fix now refuses files edited since the check (E-FIX-STALE), writes atomically, skips fixes with out-of-range edits and rolls back fixes that leave a file unparsable.
