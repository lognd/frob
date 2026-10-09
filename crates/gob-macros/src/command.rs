//! `#[derive(Command)]` expansion.

use darling::FromDeriveInput;
use darling::util::PathList;
use proc_macro2::TokenStream as TokenStream2;
use quote::quote;
use syn::DeriveInput;

use crate::doc_lines;

/// Exit-code names accepted inside `exits(...)`, paired with their variants.
const EXITS: [(&str, &str); 5] = [
    ("ok", "Ok"),
    ("negative", "Negative"),
    ("usage", "Usage"),
    ("refused", "Refused"),
    ("internal", "Internal"),
];

#[derive(Debug, FromDeriveInput)]
#[darling(attributes(command), forward_attrs(doc), supports(struct_any))]
struct CommandArgs {
    ident: syn::Ident,
    generics: syn::Generics,
    attrs: Vec<syn::Attribute>,
    verb: String,
    product: String,
    #[darling(default)]
    idempotent: bool,
    #[darling(default)]
    dry_run: bool,
    exits: PathList,
    #[darling(default)]
    deprecated: Option<String>,
    #[darling(default)]
    markdown: bool,
    #[darling(default)]
    read_only: bool,
}

/// True for lowercase words separated by single spaces (`config show`).
fn valid_verb(verb: &str) -> bool {
    !verb.is_empty()
        && verb.split(' ').all(|w| {
            !w.is_empty()
                && w.bytes()
                    .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        })
}

pub(crate) fn expand(input: &DeriveInput) -> darling::Result<TokenStream2> {
    let args = CommandArgs::from_derive_input(input)?;
    let mut errors = darling::Error::accumulator();

    if !valid_verb(&args.verb) {
        errors.push(darling::Error::custom(format!(
            "invalid verb `{}`; expected lowercase words separated by single spaces, e.g. `config show`",
            args.verb
        )));
    }
    if !args.generics.params.is_empty() {
        errors.push(darling::Error::custom(
            "#[derive(Command)] does not support generic types",
        ));
    }
    let mut exits = Vec::new();
    for path in args.exits.iter() {
        let name = path
            .get_ident()
            .map(ToString::to_string)
            .unwrap_or_default();
        match EXITS.iter().find(|(n, _)| *n == name) {
            Some((_, variant)) => {
                exits.push(syn::Ident::new(variant, proc_macro2::Span::call_site()));
            }
            None => errors.push(darling::Error::custom(format!(
                "invalid exit `{name}`; expected one of: {}",
                EXITS.map(|(n, _)| n).join(", ")
            ))),
        }
    }
    if exits.is_empty() {
        errors.push(darling::Error::custom(
            "`exits(...)` must name at least one exit code",
        ));
    }
    if let Some(form) = &args.deprecated {
        let first = form.split(' ').next().unwrap_or_default();
        if !valid_verb(first)
            || first.starts_with('-')
            || form.contains('`')
            || form.contains("  ")
            || form.ends_with(' ')
        {
            errors.push(darling::Error::custom(format!(
                "invalid deprecated form `{form}`; expected a registered verb followed by flags, e.g. `ticket show --format md`"
            )));
        } else if form == &args.verb || form.starts_with(&format!("{} ", args.verb)) {
            errors.push(darling::Error::custom(
                "a deprecated alias cannot name itself as its replacement",
            ));
        }
        if args.markdown {
            errors.push(darling::Error::custom(
                "a deprecated alias cannot declare `markdown`; the replacement owns the markdown view",
            ));
        }
    }
    let summary = doc_lines(&args.attrs)
        .into_iter()
        .find(|l| !l.trim().is_empty())
        .unwrap_or_default();
    if summary.is_empty() {
        errors.push(darling::Error::custom(
            "a command needs a `///` doc comment (its summary)",
        ));
    }
    errors.finish()?;

    let CommandArgs {
        ident,
        verb,
        product,
        idempotent,
        dry_run,
        markdown,
        read_only,
        deprecated,
        ..
    } = args;
    let deprecated = deprecated.map_or_else(
        || quote!(::core::option::Option::None),
        |form| quote!(::core::option::Option::Some(#form)),
    );
    Ok(quote! {
        impl ::gob_cli::Described for #ident {
            const META: ::gob_cli::CommandMeta = ::gob_cli::CommandMeta {
                verb: #verb,
                product: #product,
                idempotent: #idempotent,
                dry_run: #dry_run,
                exits: &[#(::gob_cli::ExitCode::#exits),*],
                summary: #summary,
                module: ::core::module_path!(),
                deprecated: #deprecated,
                markdown: #markdown,
                read_only: #read_only,
            };
        }

        ::gob_cli::inventory::submit! {
            ::gob_cli::CommandEntry::new(&<#ident as ::gob_cli::Described>::META)
        }
    })
}
