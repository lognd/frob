//! The `frob` binary: the generic product entry, then exit.

fn main() {
    gob_git::install_content_backend();
    // One process is one command: share each discovered repository for its whole run.
    let scope = gob_git::DiscoverScope::begin();
    let code = gob_product::main::<frob_cli::FrobProduct>();
    drop(scope);
    // The only process-exit call in the workspace outside gob-exec and gob-git.
    std::process::exit(code);
}
