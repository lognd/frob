use gob_cli::Command;

/// Summary.
#[derive(Command)]
#[command(verb = "x", product = "frob", exits(ok), deprecated = "x --flag")]
struct C;

fn main() {}
