use gob_cli::Command;

/// Doc.
#[derive(Command)]
#[command(verb = "x", product = "frob", exits(ok, exploded))]
struct C;

fn main() {}
