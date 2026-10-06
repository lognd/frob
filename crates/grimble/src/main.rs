//! The `grimble` binary: the generic product entry, then exit.

fn main() {
    let code = gob_product::main::<grimble::GrimbleProduct>();
    // The process-exit call of this binary, as in `frob`.
    std::process::exit(code);
}
