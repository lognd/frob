//! `#[derive(ConfigTable)]` expansion.
// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

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
    /// No default: the key must be written, and a missing key is a deserialize error.
    #[darling(default)]
    required: bool,
    /// The TOML key when it differs from the field name.
    #[darling(default)]
    rename: Option<String>,
    /// On a `rest` table's entries field: path of `fn() -> serde_json::Value`, the table schema.
    #[darling(default)]
    schema_with: Option<syn::Path>,
}

#[derive(Debug, FromDeriveInput)]
#[darling(attributes(config), forward_attrs(doc), supports(struct_named))]
#[allow(clippy::struct_excessive_bools)]
struct TableArgs {
    ident: syn::Ident,
    generics: syn::Generics,
    attrs: Vec<syn::Attribute>,
    data: darling::ast::Data<(), FieldArgs>,
    table: String,
    #[darling(default)]
    materialize: bool,
    /// Product whose file holds the table (default `frob`).
    #[darling(default)]
    product: Option<String>,
    /// The table is an array of tables (`[[x]]`).
    #[darling(default)]
    array: bool,
    /// The table's schema is reachable only through a parent field's type; it also gets `JsonSchema`.
    #[darling(default)]
    inline: bool,
    /// Dynamic-key table: one field holding every entry, deserialized transparently.
    #[darling(default)]
    rest: bool,
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

/// The `T` of `Option<T>`, or `None` when `ty` is not an `Option`.
fn option_inner(ty: &syn::Type) -> Option<&syn::Type> {
    generic_args(ty, "Option").and_then(|args| args.into_iter().next())
}

/// The type arguments of `ty` when its last path segment is `name`.
fn generic_args<'a>(ty: &'a syn::Type, name: &str) -> Option<Vec<&'a syn::Type>> {
    let syn::Type::Path(path) = ty else {
        return None;
    };
    let seg = path.path.segments.last()?;
    if seg.ident != name {
        return None;
    }
    let syn::PathArguments::AngleBracketed(args) = &seg.arguments else {
        return None;
    };
    Some(
        args.args
            .iter()
            .filter_map(|a| match a {
                syn::GenericArgument::Type(t) => Some(t),
                _ => None,
            })
            .collect(),
    )
}

/// The value type `V` of a `Map<String, V>` style type: its last type argument.
fn map_value(ty: &syn::Type) -> Option<&syn::Type> {
    let syn::Type::Path(path) = ty else {
        return None;
    };
    let seg = path.path.segments.last()?;
    let syn::PathArguments::AngleBracketed(args) = &seg.arguments else {
        return None;
    };
    let types: Vec<&syn::Type> = args
        .args
        .iter()
        .filter_map(|a| match a {
            syn::GenericArgument::Type(t) => Some(t),
            _ => None,
        })
        .collect();
    // A map has at least a key and a value type; `Vec<T>` and friends do not.
    if types.len() < 2 {
        return None;
    }
    types.last().copied()
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
    if let Some(product) = &args.product
        && !valid_table(product)
    {
        errors.push(darling::Error::custom(format!(
            "invalid product `{product}`; expected one lowercase snake_case name"
        )));
    }
    if args.rest && fields.len() != 1 {
        errors.push(darling::Error::custom(
            "a `rest` table has exactly one field: the map of entries",
        ));
    }
    if !args.generics.params.is_empty() {
        errors.push(darling::Error::custom(
            "#[derive(ConfigTable)] does not support generic types",
        ));
    }
    for f in fields {
        if f.required && (f.default.is_some() || f.enforcement) {
            errors.push(
                darling::Error::custom(
                    "a `required` field has no default and is not an enforcement knob",
                )
                .with_span(&f.ty),
            );
        }
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
    let product = args.product.clone().unwrap_or_else(|| "frob".to_owned());
    let materialize = args.materialize;
    let (array, inline) = (args.array, args.inline);
    let table_doc = doc_lines(&args.attrs).join("\n");

    let body = if args.rest {
        rest_body(ident, &fields[0])?
    } else {
        fields_body(ident, &fields)
    };
    let Body {
        items,
        deserialize,
        default_impl,
        fields_desc,
        rest_desc,
    } = body;

    let json_schema = inline.then(|| {
        let name = ident.to_string();
        quote! {
            impl ::gob_config::schemars::JsonSchema for #ident {
                fn schema_name() -> ::std::borrow::Cow<'static, str> {
                    ::std::borrow::Cow::Borrowed(#name)
                }

                fn json_schema(
                    generator: &mut ::gob_config::schemars::SchemaGenerator,
                ) -> ::gob_config::schemars::Schema {
                    let mut node = ::gob_config::table_schema(
                        &<#ident as ::gob_config::ConfigTable>::describe(),
                    );
                    if let ::gob_config::serde_json::Value::Object(map) = &mut node
                        && let ::core::option::Option::Some(
                            ::gob_config::serde_json::Value::Object(defs),
                        ) = map.remove("$defs")
                    {
                        for (key, def) in defs {
                            generator.definitions_mut().insert(key, def);
                        }
                    }
                    ::gob_config::schemars::Schema::try_from(node)
                        .unwrap_or_else(|e| panic!("table schema is not a schema: {e}"))
                }
            }
        }
    });

    Ok(quote! {
        const _: () = {
            #items

            #deserialize

            #default_impl

            impl ::gob_config::ConfigTable for #ident {
                const TABLE: &'static str = #table;
                const PRODUCT: &'static str = #product;

                fn describe() -> ::gob_config::TableDescription {
                    ::gob_config::TableDescription {
                        table: ::std::string::String::from(#table),
                        product: ::std::string::String::from(#product),
                        array: #array,
                        inline: #inline,
                        rest: #rest_desc,
                        doc: ::std::string::String::from(#table_doc),
                        materialize: #materialize,
                        fields: ::std::vec![#(#fields_desc),*],
                    }
                }
            }

            #json_schema

            ::gob_config::inventory::submit! {
                ::gob_config::TableEntry::new(<#ident as ::gob_config::ConfigTable>::describe)
            }
        };
    })
}

/// The pieces of the expansion that differ between field tables and `rest` tables.
struct Body {
    items: TokenStream2,
    deserialize: TokenStream2,
    default_impl: TokenStream2,
    fields_desc: Vec<TokenStream2>,
    rest_desc: TokenStream2,
}

/// A dynamic-key table: deserialized transparently from its single map field.
fn rest_body(ident: &syn::Ident, f: &FieldArgs) -> darling::Result<Body> {
    let name = f
        .ident
        .clone()
        .unwrap_or_else(|| unreachable!("supports(struct_named) guarantees idents"));
    let ty = &f.ty;
    let Some(value) = map_value(ty) else {
        return Err(darling::Error::custom(
            "a `rest` field must be a map type such as `IndexMap<String, V>`",
        )
        .with_span(ty));
    };
    let doc = doc_lines(&f.attrs).join("\n");
    let type_name = type_text(ty);
    let table_schema = f.schema_with.as_ref().map_or_else(
        || quote! { ::core::option::Option::None },
        |path| quote! { ::core::option::Option::Some(#path()) },
    );
    Ok(Body {
        items: quote! {},
        deserialize: quote! {
            impl<'de> ::gob_config::serde::Deserialize<'de> for #ident {
                fn deserialize<D>(deserializer: D) -> ::core::result::Result<Self, D::Error>
                where
                    D: ::gob_config::serde::Deserializer<'de>,
                {
                    ::core::result::Result::Ok(Self {
                        #name: <#ty as ::gob_config::serde::Deserialize>::deserialize(deserializer)?,
                    })
                }
            }
        },
        default_impl: quote! {
            impl ::core::default::Default for #ident {
                fn default() -> Self {
                    Self { #name: ::core::default::Default::default() }
                }
            }
        },
        fields_desc: Vec::new(),
        rest_desc: quote! {
            ::core::option::Option::Some(::gob_config::RestDescription {
                doc: ::std::string::String::from(#doc),
                type_name: ::std::string::String::from(#type_name),
                value_schema: ::gob_config::schema_of::<#value>(),
                table_schema: #table_schema,
            })
        },
    })
}

/// A table of declared fields: partial deserialization, defaults and field descriptions.
#[allow(clippy::too_many_lines)]
fn fields_body(ident: &syn::Ident, fields: &[FieldArgs]) -> Body {
    let mut default_fns = Vec::new();
    let mut partial_fields = Vec::new();
    let mut fills = Vec::new();
    let mut defaults = Vec::new();
    let mut descs = Vec::new();
    let has_required = fields.iter().any(|f| f.required);
    for (i, f) in fields.iter().enumerate() {
        let name = f
            .ident
            .clone()
            .unwrap_or_else(|| unreachable!("supports(struct_named) guarantees idents"));
        let key = f
            .rename
            .clone()
            .unwrap_or_else(|| syn::ext::IdentExt::unraw(&name).to_string());
        let ty = &f.ty;
        let optional = option_inner(ty).filter(|_| f.default.is_none() && !f.required);
        let rename_attr = f.rename.as_ref().map(|k| quote! { #[serde(rename = #k)] });
        let doc = doc_lines(&f.attrs).join("\n");
        let enforcement = f.enforcement;
        let required = f.required;

        let (schema_ty, default_toml) = if let Some(inner) = optional {
            partial_fields.push(
                quote! { #[serde(default)] #rename_attr #name: ::core::option::Option<#inner> },
            );
            fills.push(quote! { #name: partial.#name });
            defaults.push(quote! { #name: ::core::option::Option::None });
            (inner, quote! { ::std::string::String::new() })
        } else if required {
            partial_fields
                .push(quote! { #[serde(default)] #rename_attr #name: ::core::option::Option<#ty> });
            fills.push(quote! {
                #name: match partial.#name {
                    ::core::option::Option::Some(value) => value,
                    ::core::option::Option::None => {
                        return ::core::result::Result::Err(
                            <D::Error as ::gob_config::serde::de::Error>::missing_field(#key),
                        );
                    }
                }
            });
            (ty, quote! { ::std::string::String::new() })
        } else {
            let fn_name =
                syn::Ident::new(&format!("__default_{i}"), proc_macro2::Span::call_site());
            let body = f.default.as_ref().map_or_else(
                || quote! { <#ty as ::core::default::Default>::default() },
                ToTokens::to_token_stream,
            );
            default_fns.push(quote! { fn #fn_name() -> #ty { #body } });
            partial_fields
                .push(quote! { #[serde(default)] #rename_attr #name: ::core::option::Option<#ty> });
            fills.push(quote! { #name: partial.#name.unwrap_or_else(#fn_name) });
            defaults.push(quote! { #name: #fn_name() });
            (ty, quote! { ::gob_config::render_default(&#fn_name()) })
        };
        let type_name = type_text(schema_ty);
        descs.push(quote! {
            ::gob_config::FieldDescription {
                key: ::std::string::String::from(#key),
                doc: ::std::string::String::from(#doc),
                default_toml: #default_toml,
                required: #required,
                enforcement: #enforcement,
                type_name: ::std::string::String::from(#type_name),
                schema: ::gob_config::schema_of::<#schema_ty>(),
            }
        });
    }

    let default_impl = if has_required {
        quote! {}
    } else {
        quote! {
            impl ::core::default::Default for #ident {
                fn default() -> Self {
                    Self { #(#defaults,)* }
                }
            }
        }
    };
    Body {
        items: quote! {
            #(#default_fns)*

            #[derive(::gob_config::serde::Deserialize)]
            #[serde(crate = "::gob_config::serde", deny_unknown_fields)]
            struct __Partial {
                #(#partial_fields,)*
            }
        },
        deserialize: quote! {
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
        },
        default_impl,
        fields_desc: descs,
        rest_desc: quote! { ::core::option::Option::None },
    }
}
