use gob_directives::Directive;

#[derive(Directive)]
#[directive(namespace = "frob", verb = "ticket")]
struct D {
    #[arg(positional)]
    id: String,
}

fn main() {}
