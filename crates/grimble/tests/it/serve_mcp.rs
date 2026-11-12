//! `grimble serve --mcp` is taken by the token-gated server, not the tokenless generic verb.

// frob:ticket 01M3Z714XYJEHXHNWXKVXAYFQJ

use grimble::serve_mcp::requested;

// frob:tests crates/grimble/src/serve_mcp.rs::requested
#[test]
fn only_serve_with_mcp_is_taken() {
    assert!(requested(&["serve", "--mcp"]));
    assert!(requested(&["serve", "--json", "--mcp"]));
    assert!(!requested(&["serve"]));
    assert!(!requested(&["check", "--mcp"]));
    assert!(!requested::<&str>(&[]));
}

// frob:tests crates/grimble/src/serve_mcp.rs::process_args
#[test]
fn process_args_exclude_the_program_name() {
    let args = grimble::serve_mcp::process_args();
    assert_eq!(args.len() + 1, std::env::args_os().count());
}
