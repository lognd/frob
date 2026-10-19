Nested `grimble.toml` files load only from directories listed in the root `[workspace] members` (`gob_config::nested_config_dirs`); vendored, ignored and submodule paths never trigger nested loading.
