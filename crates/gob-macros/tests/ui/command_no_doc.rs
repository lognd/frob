use gob_cli::Command;

#[derive(Command)]
#[command(verb = "x", product = "frob", exits(ok))]
struct C;

fn main() {}
