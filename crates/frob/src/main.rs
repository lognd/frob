//! The `frob` binary: the generic product entry, then exit.

/// Runs the product with each discovered repository shared for the whole command.
fn run_scoped() -> i32 {
    gob_git::install_content_backend();
    // One process is one command: share each discovered repository for its whole run.
    let _scope = gob_git::DiscoverScope::begin();
    gob_product::main::<frob_cli::FrobProduct>()
}

fn main() {
    let code = run_scoped();
    // The only process-exit call in the workspace outside gob-exec and gob-git.
    std::process::exit(code);
}
