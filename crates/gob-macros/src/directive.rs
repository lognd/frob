//! `#[derive(Directive)]` expansion.

use darling::ast::{Data, Style};
use darling::util::Ignored;
use darling::{FromDeriveInput, FromField};
use proc_macro2::TokenStream as TokenStream2;
use quote::quote;
use syn::{DeriveInput, GenericArgument, PathArguments, Type};

use crate::doc_lines;

#[derive(Debug, FromDeriveInput)]
#[darling(attributes(directive), forward_attrs(doc), supports(struct_any))]
struct DirectiveArgs {
    ident: syn::Ident,
    generics: syn::Generics,
    attrs: Vec<syn::Attribute>,
    data: Data<Ignored, ArgField>,
    namespace: String,
    verb: String,
}

/// The five flags are the attribute grammar itself, not state.
#[allow(clippy::struct_excessive_bools)]
#[derive(Debug, FromField)]
#[darling(attributes(arg), forward_attrs(doc))]
struct ArgField {
    ident: Option<syn::Ident>,
    ty: Type,
    attrs: Vec<syn::Attribute>,
    #[darling(default)]
    positional: bool,
    key: Option<String>,
    #[darling(default)]
    optional: bool,
    #[darling(default)]
    list: bool,
    #[darling(default)]
    rest: bool,
    #[darling(default)]
    ticket_ref: bool,
}

/// How a field is bound to the directive's argument list.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Mode {
    Positional,
    Keyed,
    List,
    /// All remaining positionals parsed together as one `FromArgs` value.
    Rest,
}

/// Outer wrapper of a field type.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Shape {
    Plain,
    Option,
    Vec,
}

/// Peel one `Option<T>` or `Vec<T>` layer off `ty`.
fn shape(ty: &Type) -> (Shape, &Type) {
    if let Type::Path(p) = ty
        && p.qself.is_none()
        && let Some(seg) = p.path.segments.last()
        && let PathArguments::AngleBracketed(ab) = &seg.arguments
        && ab.args.len() == 1
        && let Some(GenericArgument::Type(inner)) = ab.args.first()
    {
        match seg.ident.to_string().as_str() {
            "Option" => return (Shape::Option, inner),
            "Vec" => return (Shape::Vec, inner),
            _ => {}
        }
    }
    (Shape::Plain, ty)
}

/// True for lowercase identifier-like words (`frob`, `ticket`, `my-verb`).
fn valid_word(s: &str, allow_dash: bool) -> bool {
    let mut chars = s.chars();
    chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| {
            c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' || (allow_dash && c == '-')
        })
}

/// A validated field ready for code generation.
struct Planned {
    ident: syn::Ident,
    mode: Mode,
    optional: bool,
    key: Option<String>,
    ty: Type,
    inner: Type,
    ticket_ref: bool,
    summary: String,
}

/// Validate one field, pushing every problem onto `errors`.
fn plan_field(f: &ArgField, errors: &mut darling::error::Accumulator) -> Option<Planned> {
    let ident = f.ident.clone()?;
    let (sh, inner) = shape(&f.ty);
    let chosen = usize::from(f.positional)
        + usize::from(f.key.is_some())
        + usize::from(f.list)
        + usize::from(f.rest);
    if chosen > 1 {
        errors.push(
            darling::Error::custom(format!(
                "field `{ident}`: choose one of `positional`, `key = \"..\"`, `list`, `rest`"
            ))
            .with_span(&ident),
        );
        return None;
    }
    let mode = if f.rest {
        Mode::Rest
    } else if f.list {
        Mode::List
    } else if f.key.is_some() {
        Mode::Keyed
    } else {
        Mode::Positional
    };
    if let Some(key) = &f.key
        && !valid_word(key, true)
    {
        errors.push(
            darling::Error::custom(format!("field `{ident}`: invalid key `{key}`"))
                .with_span(&ident),
        );
    }
    let mut bad = |msg: &str| {
        errors.push(darling::Error::custom(format!("field `{ident}`: {msg}")).with_span(&ident));
    };
    match (mode, sh) {
        (Mode::List, Shape::Vec) | (Mode::Rest, Shape::Plain) => {}
        (Mode::List, _) => bad("`list` needs a `Vec<T>` field"),
        (Mode::Rest, _) => bad("`rest` needs a plain field type implementing `FromArgs`"),
        (_, Shape::Vec) => bad("a `Vec<T>` field needs `#[arg(list)]`"),
        _ => {}
    }
    if f.optional && sh != Shape::Option {
        bad("`optional` needs an `Option<T>` field");
    }
    if sh == Shape::Option && mode == Mode::List {
        bad("a list cannot be optional");
    }
    let summary = doc_lines(&f.attrs)
        .into_iter()
        .find(|l| !l.trim().is_empty())
        .unwrap_or_default();
    Some(Planned {
        ident,
        mode,
        optional: sh == Shape::Option,
        key: f.key.clone(),
        ty: f.ty.clone(),
        inner: inner.clone(),
        ticket_ref: f.ticket_ref,
        summary,
    })
}

/// Cross-field rules: ordering of positionals and unique keys.
fn check_order(planned: &[Planned], errors: &mut darling::error::Accumulator) {
    let mut seen_list = false;
    let mut seen_optional = false;
    let mut keys: Vec<&str> = Vec::new();
    for p in planned {
        match p.mode {
            Mode::Positional => {
                if seen_list {
                    errors.push(
                        darling::Error::custom(format!(
                            "positional `{}` follows the `list` field",
                            p.ident
                        ))
                        .with_span(&p.ident),
                    );
                }
                if seen_optional && !p.optional {
                    errors.push(
                        darling::Error::custom(format!(
                            "required positional `{}` follows an optional one",
                            p.ident
                        ))
                        .with_span(&p.ident),
                    );
                }
                seen_optional |= p.optional;
            }
            Mode::List | Mode::Rest => {
                if seen_list {
                    errors.push(
                        darling::Error::custom("only one `list` or `rest` field is allowed")
                            .with_span(&p.ident),
                    );
                }
                seen_list = true;
            }
            Mode::Keyed => {
                let key = p.key.as_deref().unwrap_or_default();
                if keys.contains(&key) {
                    errors.push(
                        darling::Error::custom(format!("duplicate key `{key}`"))
                            .with_span(&p.ident),
                    );
                }
                keys.push(key);
            }
        }
    }
}

pub(crate) fn expand(input: &DeriveInput) -> darling::Result<TokenStream2> {
    let args = DirectiveArgs::from_derive_input(input)?;
    let mut errors = darling::Error::accumulator();

    if !valid_word(&args.namespace, false) {
        errors.push(darling::Error::custom(format!(
            "invalid namespace `{}`; expected lowercase letters, digits and `_`",
            args.namespace
        )));
    }
    if !valid_word(&args.verb, true) {
        errors.push(darling::Error::custom(format!(
            "invalid verb `{}`; expected lowercase letters, digits, `_` and `-`",
            args.verb
        )));
    }
    if !args.generics.params.is_empty() {
        errors.push(darling::Error::custom(
            "#[derive(Directive)] does not support generic types",
        ));
    }
    let summary = doc_lines(&args.attrs)
        .into_iter()
        .find(|l| !l.trim().is_empty())
        .unwrap_or_default();
    if summary.is_empty() {
        errors.push(darling::Error::custom(
            "a directive needs a `///` doc comment (its summary)",
        ));
    }
    let fields = match &args.data {
        Data::Struct(f) if f.style == Style::Tuple => {
            errors.push(darling::Error::custom(
                "#[derive(Directive)] needs named fields",
            ));
            Vec::new()
        }
        Data::Struct(f) => f.fields.iter().collect::<Vec<_>>(),
        Data::Enum(_) => Vec::new(),
    };
    let planned: Vec<Planned> = fields
        .iter()
        .filter_map(|f| plan_field(f, &mut errors))
        .collect();
    check_order(&planned, &mut errors);
    errors.finish()?;

    let DirectiveArgs {
        ident,
        namespace,
        verb,
        ..
    } = args;
    let metas = planned.iter().map(meta_tokens);
    let binds = planned.iter().map(bind_tokens);
    let names = planned.iter().map(|p| &p.ident);
    let keys: Vec<&str> = planned.iter().filter_map(|p| p.key.as_deref()).collect();
    Ok(quote! {
        impl #ident {
            /// Static metadata for this directive, generated by `#[derive(Directive)]`.
            pub const META: ::gob_directives::DirectiveMeta = ::gob_directives::DirectiveMeta {
                namespace: #namespace,
                verb: #verb,
                summary: #summary,
                args: &[#(#metas),*],
            };
        }

        impl ::gob_directives::Directive for #ident {
            const NAMESPACE: &'static str = #namespace;
            const VERB: &'static str = #verb;

            fn parse_args(
                args: &::gob_directives::ArgList,
            ) -> ::core::result::Result<Self, ::gob_directives::ArgError> {
                let mut cur = ::gob_directives::Cursor::new(args);
                #(#binds)*
                cur.finish(&[#(#keys),*])?;
                ::core::result::Result::Ok(Self { #(#names),* })
            }
        }

        ::gob_directives::inventory::submit! {
            ::gob_directives::DirectiveEntry::new(
                &#ident::META,
                ::gob_directives::validate::<#ident>,
            )
        }
    })
}

/// The `ArgMeta` literal for one field.
fn meta_tokens(p: &Planned) -> TokenStream2 {
    let name = p.ident.to_string();
    let key = if let Some(k) = &p.key {
        quote!(::core::option::Option::Some(#k))
    } else {
        quote!(::core::option::Option::None)
    };
    let positional = p.mode != Mode::Keyed;
    let list = matches!(p.mode, Mode::List | Mode::Rest);
    let optional = p.optional;
    let ticket_ref = p.ticket_ref;
    let summary = &p.summary;
    let inner = &p.inner;
    let kind = if p.mode == Mode::Rest {
        quote!(<#inner as ::gob_directives::FromArgs>::KIND)
    } else {
        quote!(<#inner as ::gob_directives::FromArg>::KIND)
    };
    quote! {
        ::gob_directives::ArgMeta {
            name: #name,
            key: #key,
            positional: #positional,
            list: #list,
            optional: #optional,
            kind: #kind,
            ticket_ref: #ticket_ref,
            summary: #summary,
        }
    }
}

/// The `let` that pulls one field out of the cursor.
fn bind_tokens(p: &Planned) -> TokenStream2 {
    let id = &p.ident;
    let name = p.ident.to_string();
    let ty = &p.ty;
    let inner = &p.inner;
    let key = p.key.as_deref().unwrap_or_default();
    match (p.mode, p.optional) {
        (Mode::Positional, false) => quote!(let #id = cur.positional::<#ty>(#name)?;),
        (Mode::Positional, true) => quote!(let #id = cur.positional_opt::<#inner>(#name)?;),
        (Mode::Keyed, false) => quote!(let #id = cur.keyed::<#ty>(#key)?;),
        (Mode::Keyed, true) => quote!(let #id = cur.keyed_opt::<#inner>(#key)?;),
        (Mode::Rest, _) => quote!(let #id = cur.rest::<#ty>(#name)?;),
        (Mode::List, _) => quote!(let #id = cur.list::<#inner>(#name)?;),
    }
}
