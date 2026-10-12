gob-walk no longer depends on gob-git: it defines a ContentBackend trait that gob-git implements and the binaries install, so gix leaves the dependency tree of gob-walk, gob-ir, gob-symbols and grimble-model.
gob-walk no longer reads frob.toml either: callers pass the ledger directory (gob-config::ledger_dir) to Roles::new.
