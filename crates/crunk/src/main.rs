//! The `crunk` binary: build the CLI, verify the rule registry, exit.

fn main() {
    let cli = crunk::cli();
    let code = match gob_rules::Registry::global().verify_unique() {
        Ok(()) => cli.run(std::env::args_os().skip(1)),
        Err(e) => cli.fail_startup(e),
    };
    // The process-exit call of this binary, as in `frob` and `grimble`.
    std::process::exit(code);
}
