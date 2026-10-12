//! The `frob` binary: the generic product entry, then exit.

fn main() {
    gob_git::install_content_backend();
    let code = gob_product::main::<frob_cli::FrobProduct>();
    // The only process-exit call in the workspace outside gob-exec and gob-git.
    std::process::exit(code);
}
