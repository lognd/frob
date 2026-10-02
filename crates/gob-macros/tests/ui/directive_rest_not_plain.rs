use gob_directives::Directive;

/// Doc.
#[derive(Directive)]
#[directive(namespace = "frob", verb = "ticket")]
struct D {
    #[arg(rest)]
    id: Vec<String>,
}

fn main() {}
