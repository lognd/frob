//! The `crunk` binary: the generic product entry, then exit.

fn main() {
    // frob:ticket 01M4RN89XGXSXMSF2HV2FPSG41
    // Git-normalized digests need the content backend installed before any walk (as in frob).
    gob_git::install_content_backend();
    let code = gob_product::main::<crunk::CrunkProduct>();
    // The process-exit call of this binary, as in `frob` and `grimble`.
    std::process::exit(code);
}
