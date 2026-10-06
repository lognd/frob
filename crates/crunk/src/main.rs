//! The `crunk` binary: the generic product entry, then exit.

fn main() {
    let code = gob_product::main::<crunk::CrunkProduct>();
    // The process-exit call of this binary, as in `frob` and `grimble`.
    std::process::exit(code);
}
