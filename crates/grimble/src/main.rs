//! The `grimble` binary: build the CLI, verify the rule registry, exit.

fn main() {
    let cli = grimble::cli();
    let code = match gob_rules::Registry::global().verify_unique() {
        Ok(()) => cli.run(std::env::args_os().skip(1)),
        Err(e) => cli.fail_startup(e),
    };
    // The process-exit call of this binary, as in `frob`.
    std::process::exit(code);
}
