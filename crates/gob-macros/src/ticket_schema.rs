//! `#[derive(TicketSchema)]` expansion.

use darling::ast::{Data, Style};
use darling::util::Ignored;
use darling::{FromDeriveInput, FromField};
use proc_macro2::TokenStream as TokenStream2;
use quote::quote;
use syn::{DeriveInput, Expr, ExprLit, Lit, Type};

use crate::doc_lines;

/// Kinds accepted by `#[ticket(kind = "..")]`.
const KINDS: &[&str] = &["enum", "list", "scalar", "table"];

#[derive(Debug, FromDeriveInput)]
#[darling(attributes(ticket), forward_attrs(doc), supports(struct_named))]
struct SchemaArgs {
    ident: syn::Ident,
    generics: syn::Generics,
    attrs: Vec<syn::Attribute>,
    data: Data<Ignored, SchemaField>,
    /// Path of the crate that defines the runtime (`frob_ledger` by default).
    #[darling(rename = "crate")]
    crate_path: Option<syn::Path>,
}

/// The flags are the attribute grammar itself, not state.
#[allow(clippy::struct_excessive_bools)]
#[derive(Debug, FromField)]
#[darling(attributes(ticket), forward_attrs(doc))]
struct SchemaField {
    ident: Option<syn::Ident>,
    ty: Type,
    attrs: Vec<syn::Attribute>,
    #[darling(default)]
    required: bool,
    #[darling(default)]
    settable: bool,
    default: Option<Expr>,
    since: Option<String>,
    kind: Option<String>,
    key: Option<String>,
}

/// True when the outermost path segment of `ty` is `name`.
fn outer_is(ty: &Type, name: &str) -> bool {
    matches!(ty, Type::Path(p) if p.path.segments.last().is_some_and(|s| s.ident == name))
}

/// Render a `default = <expr>` as TOML text: strings are quoted, the rest is verbatim.
fn default_toml(e: &Expr) -> String {
    match e {
        Expr::Lit(ExprLit {
            lit: Lit::Str(s), ..
        }) => format!("{:?}", s.value()),
        other => quote!(#other).to_string(),
    }
}

/// Join all doc lines into one space-separated sentence.
fn joined_doc(attrs: &[syn::Attribute]) -> String {
    doc_lines(attrs)
        .into_iter()
        .filter(|l| !l.trim().is_empty())
        .collect::<Vec<_>>()
        .join(" ")
}

/// One validated field's `TicketFieldDescription` literal.
fn field_tokens(
    f: &SchemaField,
    krate: &syn::Path,
    errors: &mut darling::error::Accumulator,
) -> Option<TokenStream2> {
    let ident = f.ident.as_ref()?;
    let mut bad = |msg: &str| {
        errors.push(darling::Error::custom(format!("field `{ident}`: {msg}")).with_span(ident));
    };
    let doc = joined_doc(&f.attrs);
    let mut ok = true;
    if doc.is_empty() {
        bad("needs a `///` doc comment");
        ok = false;
    }
    if f.required && f.default.is_some() {
        bad("`required` cannot be combined with `default`");
        ok = false;
    }
    let kind = match f.kind.as_deref() {
        Some(k) if KINDS.contains(&k) => k,
        Some(k) => {
            bad(&format!(
                "invalid kind `{k}`; expected one of: {}",
                KINDS.join(", ")
            ));
            return None;
        }
        None if outer_is(&f.ty, "Vec") => "list",
        None => "scalar",
    };
    if !ok {
        return None;
    }
    let key = f
        .key
        .clone()
        .unwrap_or_else(|| ident.to_string().trim_start_matches("r#").to_owned());
    let ty = &f.ty;
    let type_name = quote!(#ty).to_string().replace(' ', "");
    let required = f.required;
    let settable = f.settable;
    let default = f.default.as_ref().map(default_toml).map_or_else(
        || quote!(::core::option::Option::None),
        |d| quote!(::core::option::Option::Some(#d)),
    );
    let since = f.since.as_ref().map_or_else(
        || quote!(::core::option::Option::None),
        |s| quote!(::core::option::Option::Some(#s)),
    );
    let kind_ident = syn::Ident::new(
        match kind {
            "enum" => "Enum",
            "list" => "List",
            "table" => "Table",
            _ => "Scalar",
        },
        proc_macro2::Span::call_site(),
    );
    Some(quote! {
        #krate::schema::TicketFieldDescription {
            key: #key,
            doc: #doc,
            type_name: #type_name,
            kind: #krate::schema::TicketFieldKind::#kind_ident,
            required: #required,
            settable: #settable,
            default_toml: #default,
            since: #since,
        }
    })
}

pub(crate) fn expand(input: &DeriveInput) -> darling::Result<TokenStream2> {
    let args = SchemaArgs::from_derive_input(input)?;
    let mut errors = darling::Error::accumulator();
    if !args.generics.params.is_empty() {
        errors.push(darling::Error::custom(
            "#[derive(TicketSchema)] does not support generic types",
        ));
    }
    let doc = joined_doc(&args.attrs);
    if doc.is_empty() {
        errors.push(darling::Error::custom(
            "a ticket schema needs a `///` doc comment",
        ));
    }
    let krate = args
        .crate_path
        .clone()
        .unwrap_or_else(|| syn::parse_quote!(::frob_ledger));
    let fields: Vec<&SchemaField> = match &args.data {
        Data::Struct(f) if f.style == Style::Struct => f.fields.iter().collect(),
        _ => Vec::new(),
    };
    let metas: Vec<TokenStream2> = fields
        .iter()
        .filter_map(|f| field_tokens(f, &krate, &mut errors))
        .collect();
    errors.finish()?;

    let ident = &args.ident;
    let name = ident.to_string();
    Ok(quote! {
        impl #krate::schema::TicketSchema for #ident {
            fn describe() -> &'static #krate::schema::TicketSchemaDescription {
                static DESCRIPTION: #krate::schema::TicketSchemaDescription =
                    #krate::schema::TicketSchemaDescription {
                        name: #name,
                        doc: #doc,
                        fields: &[#(#metas),*],
                    };
                &DESCRIPTION
            }
        }

        impl #ident {
            /// The JSON schema of this ticket document, built from its description.
            pub fn json_schema() -> #krate::schema::SchemaDocument {
                <Self as #krate::schema::TicketSchema>::describe().json_schema()
            }
        }

        #krate::schema::inventory::submit! {
            #krate::schema::TicketSchemaEntry::new(
                <#ident as #krate::schema::TicketSchema>::describe,
            )
        }
    })
}
