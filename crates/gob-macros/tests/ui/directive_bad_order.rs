use gob_directives::Directive;

/// Doc.
#[derive(Directive)]
#[directive(namespace = "frob", verb = "ticket")]
struct D {
    #[arg(positional)]
    first: Option<String>,
    #[arg(positional)]
    second: String,
    #[arg(key = "k", optional)]
    third: String,
}

fn main() {}
