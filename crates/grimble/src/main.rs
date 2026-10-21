//! The `grimble` binary: the generic product entry, then exit.

fn main() {
    gob_git::install_content_backend();
    gob_plan::examples::install_model_reader(grimble_check::example_model::read_example_model);
    let code = gob_product::main::<grimble::GrimbleProduct>();
    // The process-exit call of this binary, as in `frob`.
    std::process::exit(code);
}
