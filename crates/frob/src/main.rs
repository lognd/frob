//! The `frob` binary: build the CLI, verify the rule registry, exit.

fn main() {
    let cli = frob_cli::cli();
    let code = match gob_rules::Registry::global().verify_unique() {
        Ok(()) => cli.run(std::env::args_os().skip(1)),
        Err(e) => cli.fail_startup(e),
    };
    // The only process-exit call in the workspace outside gob-exec and gob-git.
    std::process::exit(code);
}
