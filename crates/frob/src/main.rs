//! The `frob` binary: the generic product entry, then exit.

fn main() {
    let code = gob_product::main::<frob_cli::FrobProduct>();
    // The only process-exit call in the workspace outside gob-exec and gob-git.
    std::process::exit(code);
}
