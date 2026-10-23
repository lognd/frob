//! `grimble serve --mcp`: the token-gated read-only MCP server, taken before the generic root.
//!
//! The generic `serve` verb of `gob-cli` has no token; grimble overrides it here with
//! [`grimble_serve::launch`] so every request must present the per-launch token (D29).

// frob:ticket 01M3Z714XYJEHXHNWXKVXAYFQJ

use std::ffi::OsStr;
use std::io;

/// True when `args` (without the program name) ask for `serve --mcp`.
pub fn requested<S: AsRef<OsStr>>(args: &[S]) -> bool {
    args.first().is_some_and(|a| a.as_ref() == "serve")
        && args.iter().any(|a| a.as_ref() == "--mcp")
}

/// Run the token-gated MCP server on stdio rooted at the working directory; the exit code.
pub fn run() -> i32 {
    let root = match std::env::current_dir() {
        Ok(root) => root,
        Err(e) => {
            tracing::error!(error = %e, "serve: no working directory");
            return 1;
        }
    };
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    let mut stderr = io::stderr().lock();
    match grimble_serve::launch(&root, stdin.lock(), &mut stdout, &mut stderr) {
        Ok(()) => 0,
        Err(e) => {
            tracing::error!(error = %e, "serve: transport failed");
            1
        }
    }
}

/// The process arguments after the program name.
pub fn process_args() -> Vec<std::ffi::OsString> {
    std::env::args_os().skip(1).collect()
}
