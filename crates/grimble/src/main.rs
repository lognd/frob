//! The `grimble` binary: the generic product entry, then exit.

fn main() {
    gob_git::install_content_backend();
    gob_plan::examples::install_model_reader(grimble_check::example_model::read_example_model);
    if grimble::serve_mcp::requested(&grimble::serve_mcp::process_args()) {
        std::process::exit(grimble::serve_mcp::run());
    }
    let code = gob_product::main::<grimble::GrimbleProduct>();
    // The process-exit call of this binary, as in `frob`.
    std::process::exit(code);
}
