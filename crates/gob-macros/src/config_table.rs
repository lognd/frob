//! `#[derive(ConfigTable)]` expansion.

use darling::{FromDeriveInput, FromField};
use proc_macro2::TokenStream as TokenStream2;
use quote::{ToTokens, quote};
use syn::DeriveInput;

use crate::doc_lines;

#[derive(Debug, Clone, FromField)]
#[darling(attributes(config), forward_attrs(doc))]
struct FieldArgs {
    ident: Option<syn::Ident>,
    ty: syn::Type,
    attrs: Vec<syn::Attribute>,
    #[darling(default)]
    default: Option<syn::Expr>,
    #[darling(default)]
    enforcement: bool,
}

#[derive(Debug, FromDeriveInput)]
#[darling(attributes(config), forward_attrs(doc), supports(struct_named))]
struct TableArgs {
    ident: syn::Ident,
    generics: syn::Generics,
    attrs: Vec<syn::Attribute>,
    data: darling::ast::Data<(), FieldArgs>,
    table: String,
    #[darling(default)]
    materialize: bool,
}

/// True for non-empty dotted paths of lowercase snake segments.
fn valid_table(table: &str) -> bool {
    !table.is_empty()
        && table.split('.').all(|seg| {
            !seg.is_empty()
                && seg
                    .bytes()
                    .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
        })
}

/// Render a type compactly for the `type_name` description field.
fn type_text(ty: &syn::Type) -> String {
    ty.to_token_stream()
        .to_string()
        .replace(' ', "")
        .replace(',', ", ")
}

/// Reject bad table paths, generics and enforcement fields without defaults.
fn validate(args: &TableArgs, fields: &[FieldArgs]) -> darling::Result<()> {
    let mut errors = darling::Error::accumulator();
    if !valid_table(&args.table) {
        errors.push(darling::Error::custom(format!(
            "invalid table `{}`; expected dotted lowercase snake_case segments",
            args.table
        )));
    }
    if !args.generics.params.is_empty() {
        errors.push(darling::Error::custom(
            "#[derive(ConfigTable)] does not support generic types",
        ));
    }
    for f in fields {
        if f.enforcement && f.default.is_none() {
            let name = f
                .ident
                .as_ref()
                .map(ToString::to_string)
                .unwrap_or_default();
            errors.push(
                darling::Error::custom(format!(
                    "enforcement field `{name}` needs `#[config(default = ...)]`: a materialized knob must have a written default"
                ))
                .with_span(&f.ty),
            );
        }
    }
    errors.finish()
}

pub(crate) fn expand(input: &DeriveInput) -> darling::Result<TokenStream2> {
    let args = TableArgs::from_derive_input(input)?;
    let fields = args
        .data
        .clone()
        .take_struct()
        .map(|s| s.fields)
        .unwrap_or_default();
    validate(&args, &fields)?;

    let ident = &args.ident;
    let table = &args.table;
    let materialize = args.materialize;
    let table_doc = doc_lines(&args.attrs).join("\n");

    let mut default_fns = Vec::new();
    let mut partial_fields = Vec::new();
    let mut fills = Vec::new();
    let mut defaults = Vec::new();
    let mut descs = Vec::new();
    for (i, f) in fields.iter().enumerate() {
        let name = f
            .ident
            .clone()
            .unwrap_or_else(|| unreachable!("supports(struct_named) guarantees idents"));
        let key = syn::ext::IdentExt::unraw(&name).to_string();
        let ty = &f.ty;
        let fn_name = syn::Ident::new(&format!("__default_{i}"), proc_macro2::Span::call_site());
        let body = f.default.as_ref().map_or_else(
            || quote! { <#ty as ::core::default::Default>::default() },
            ToTokens::to_token_stream,
        );
        default_fns.push(quote! { fn #fn_name() -> #ty { #body } });
        partial_fields.push(quote! { #[serde(default)] #name: ::core::option::Option<#ty> });
        fills.push(quote! { #name: partial.#name.unwrap_or_else(#fn_name) });
        defaults.push(quote! { #name: #fn_name() });
        let doc = doc_lines(&f.attrs).join("\n");
        let enforcement = f.enforcement;
        let type_name = type_text(ty);
        descs.push(quote! {
            ::gob_config::FieldDescription {
                key: ::std::string::String::from(#key),
                doc: ::std::string::String::from(#doc),
                default_toml: ::gob_config::render_default(&#fn_name()),
                enforcement: #enforcement,
                type_name: ::std::string::String::from(#type_name),
                schema: ::gob_config::schema_of::<#ty>(),
            }
        });
    }

    Ok(quote! {
        const _: () = {
            #(#default_fns)*

            #[derive(::gob_config::serde::Deserialize)]
            #[serde(crate = "::gob_config::serde", deny_unknown_fields)]
            struct __Partial {
                #(#partial_fields,)*
            }

            impl<'de> ::gob_config::serde::Deserialize<'de> for #ident {
                fn deserialize<D>(deserializer: D) -> ::core::result::Result<Self, D::Error>
                where
                    D: ::gob_config::serde::Deserializer<'de>,
                {
                    let partial =
                        <__Partial as ::gob_config::serde::Deserialize>::deserialize(deserializer)?;
                    ::core::result::Result::Ok(Self { #(#fills,)* })
                }
            }

            impl ::core::default::Default for #ident {
                fn default() -> Self {
                    Self { #(#defaults,)* }
                }
            }

            impl ::gob_config::ConfigTable for #ident {
                const TABLE: &'static str = #table;

                fn describe() -> ::gob_config::TableDescription {
                    ::gob_config::TableDescription {
                        table: ::std::string::String::from(#table),
                        doc: ::std::string::String::from(#table_doc),
                        materialize: #materialize,
                        fields: ::std::vec![#(#descs),*],
                    }
                }
            }

            ::gob_config::inventory::submit! {
                ::gob_config::TableEntry::new(<#ident as ::gob_config::ConfigTable>::describe)
            }
        };
    })
}
