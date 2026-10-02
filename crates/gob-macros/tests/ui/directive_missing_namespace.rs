use gob_directives::Directive;

/// Doc.
#[derive(Directive)]
#[directive(verb = "ticket")]
struct D {
    #[arg(positional)]
    id: String,
}

fn main() {}
