use gob_cli::Command;

/// Summary.
#[derive(Command)]
#[command(verb = "x", product = "frob", exits(ok), deprecated = "--only-flag")]
struct C;

fn main() {}
