//! The `grimble` binary: the generic product entry, then exit.

/// Run the product (or the MCP server when asked) and return its exit code.
fn run() -> i32 {
    gob_git::install_content_backend();
    gob_plan::examples::install_model_reader(grimble_check::example_model::read_example_model);
    if grimble::serve_mcp::requested(&grimble::serve_mcp::process_args()) {
        return grimble::serve_mcp::run();
    }
    gob_product::main::<grimble::GrimbleProduct>()
}

fn main() {
    let code = run();
    // The process-exit call of this binary, as in `frob`.
    std::process::exit(code);
}
