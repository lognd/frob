//! Proc macros for the goblins: `#[derive(Rule)]`, `#[derive(ConfigTable)]`,
//! `#[derive(Command)]` and `#[derive(Directive)]`.
//!
//! Do not depend on this crate directly: use `gob_rules::Rule`, which
//! re-exports the derive together with the runtime it expands against
//! (likewise `gob_config::ConfigTable`, `gob_cli::Command` and
//! `gob_directives::Directive`).

// The darling derive output trips this pedantic lint; nothing we can edit.
#![allow(clippy::needless_continue)]

mod command;
mod config_table;
mod directive;

use darling::{FromDeriveInput, FromMeta};
use proc_macro::TokenStream;
use proc_macro2::TokenStream as TokenStream2;
use quote::quote;
use syn::{DeriveInput, Expr, ExprLit, ExprPath, Lit, parse_macro_input};

/// An enum-like attribute value written as a bare ident or a string.
#[derive(Debug)]
struct Choice(String);

impl FromMeta for Choice {
    fn from_expr(expr: &Expr) -> darling::Result<Self> {
        match expr {
            Expr::Path(ExprPath { path, .. }) if path.get_ident().is_some() => Ok(Choice(
                path.get_ident()
                    .map(ToString::to_string)
                    .unwrap_or_default(),
            )),
            Expr::Lit(ExprLit {
                lit: Lit::Str(s), ..
            }) => Ok(Choice(s.value())),
            other => Err(darling::Error::unexpected_expr_type(other)),
        }
    }
}

impl Choice {
    /// Resolve against the allowed variant names, erroring on a miss.
    fn pick(&self, what: &str, allowed: &[&str]) -> darling::Result<syn::Ident> {
        if allowed.contains(&self.0.as_str()) {
            Ok(syn::Ident::new(&self.0, proc_macro2::Span::call_site()))
        } else {
            Err(darling::Error::custom(format!(
                "invalid {what} `{}`; expected one of: {}",
                self.0,
                allowed.join(", ")
            )))
        }
    }
}

#[derive(Debug, FromDeriveInput)]
#[darling(attributes(rule), forward_attrs(doc), supports(struct_any, enum_any))]
struct RuleArgs {
    ident: syn::Ident,
    generics: syn::Generics,
    attrs: Vec<syn::Attribute>,
    id: String,
    slug: String,
    family: String,
    #[darling(default = "default_product")]
    product: String,
    severity: Choice,
    tier: Choice,
    scope: Choice,
    fix: Choice,
    version: u32,
    #[darling(default = "default_since")]
    since: String,
}

fn default_product() -> String {
    "frob".to_owned()
}

fn default_since() -> String {
    "2.0.0".to_owned()
}

/// True when `id` is 2..=6 uppercase letters followed by exactly 3 digits.
fn valid_id(id: &str) -> Option<&str> {
    let split = id.len().checked_sub(3)?;
    let (fam, digits) = id.split_at_checked(split)?;
    let ok = (2..=6).contains(&fam.len())
        && fam.bytes().all(|b| b.is_ascii_uppercase())
        && digits.bytes().all(|b| b.is_ascii_digit());
    ok.then_some(fam)
}

/// True for non-empty lowercase kebab-case.
fn valid_slug(slug: &str) -> bool {
    !slug.is_empty()
        && !slug.starts_with('-')
        && !slug.ends_with('-')
        && !slug.contains("--")
        && slug
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

/// Collect `///` lines (trimmed of one leading space) from forwarded attrs.
pub(crate) fn doc_lines(attrs: &[syn::Attribute]) -> Vec<String> {
    attrs
        .iter()
        .filter_map(|a| match &a.meta {
            syn::Meta::NameValue(nv) => match &nv.value {
                Expr::Lit(ExprLit {
                    lit: Lit::Str(s), ..
                }) => {
                    let v = s.value();
                    Some(v.strip_prefix(' ').unwrap_or(&v).trim_end().to_owned())
                }
                _ => None,
            },
            _ => None,
        })
        .collect()
}

fn expand(input: &DeriveInput) -> darling::Result<TokenStream2> {
    let args = RuleArgs::from_derive_input(input)?;
    let mut errors = darling::Error::accumulator();

    let fam = valid_id(&args.id);
    if fam.is_none() {
        errors.push(darling::Error::custom(format!(
            "invalid rule id `{}`; expected FAMILY (2-6 uppercase letters) + 3 digits, e.g. COV006",
            args.id
        )));
    }
    if fam.is_some_and(|f| f != args.family) {
        errors.push(darling::Error::custom(format!(
            "family `{}` does not match the prefix of id `{}`",
            args.family, args.id
        )));
    }
    if !valid_slug(&args.slug) {
        errors.push(darling::Error::custom(format!(
            "invalid slug `{}`; expected lowercase kebab-case",
            args.slug
        )));
    }
    let severity = errors.handle(
        args.severity
            .pick("severity", &["Error", "Warn", "Advisory", "Unresolved"]),
    );
    let tier = errors.handle(args.tier.pick("tier", &["Universal", "Lang"]));
    let scope = errors.handle(args.scope.pick("scope", &["File", "Repo"]));
    let fix = errors.handle(
        args.fix
            .pick("fix", &["Manual", "Deterministic", "VerifyCommit", "FixIt"]),
    );

    if !args.generics.params.is_empty() {
        errors.push(darling::Error::custom(
            "#[derive(Rule)] does not support generic types",
        ));
    }
    let docs = doc_lines(&args.attrs);
    let summary = docs
        .iter()
        .find(|l| !l.trim().is_empty())
        .cloned()
        .unwrap_or_default();
    if summary.is_empty() {
        errors.push(darling::Error::custom(
            "a rule needs a `///` doc comment (its summary and explanation)",
        ));
    }
    errors.finish()?;
    let (severity, tier, scope, fix) = (
        severity.unwrap_or_else(|| unreachable!("finish() errs when a pick failed")),
        tier.unwrap_or_else(|| unreachable!("finish() errs when a pick failed")),
        scope.unwrap_or_else(|| unreachable!("finish() errs when a pick failed")),
        fix.unwrap_or_else(|| unreachable!("finish() errs when a pick failed")),
    );
    let explanation = docs.join("\n");
    let RuleArgs {
        ident,
        id,
        slug,
        family,
        product,
        version,
        since,
        ..
    } = args;
    Ok(quote! {
        impl #ident {
            /// Static metadata for this rule, generated by `#[derive(Rule)]`.
            pub const META: ::gob_rules::RuleMeta = ::gob_rules::RuleMeta {
                id: #id,
                slug: #slug,
                family: #family,
                product: #product,
                severity: ::gob_rules::Severity::#severity,
                summary: #summary,
                explanation: #explanation,
                tier: ::gob_rules::Tier::#tier,
                scope: ::gob_rules::Scope::#scope,
                fix: ::gob_rules::FixKind::#fix,
                version: #version,
                since: #since,
                module: ::core::module_path!(),
            };
        }

        impl ::gob_rules::Rule for #ident {
            fn meta(&self) -> &'static ::gob_rules::RuleMeta {
                &Self::META
            }
        }

        ::gob_rules::inventory::submit! {
            ::gob_rules::RuleEntry::new(&#ident::META)
        }
    })
}

/// Derive `gob_rules::Rule` plus an `inventory` registration for the type.
///
/// Attributes: `#[rule(id, slug, family, severity, tier, scope, fix, version)]`
/// with optional `product` (default "frob") and `since` (default "2.0.0").
/// The explanation comes from the item's `///` doc comment.
#[proc_macro_derive(Rule, attributes(rule))]
pub fn derive_rule(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    match expand(&input) {
        Ok(ts) => ts.into(),
        Err(e) => e.write_errors().into(),
    }
}

/// Derive `gob_config::ConfigTable`, `Default`, `Deserialize` and an inventory entry.
///
/// Struct attribute `#[config(table = "tickets", materialize)]`; field attribute
/// `#[config(default = <expr>, enforcement)]`. `///` docs become the generated
/// documentation. An `enforcement` field must declare a default.
#[proc_macro_derive(ConfigTable, attributes(config))]
pub fn derive_config_table(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    match config_table::expand(&input) {
        Ok(ts) => ts.into(),
        Err(e) => e.write_errors().into(),
    }
}

/// Derive `gob_cli::Described` plus an `inventory` registration for a verb.
///
/// Attribute `#[command(verb = "doctor", product = "frob", idempotent = true,
/// dry_run, exits(ok, refused))]`; `idempotent` and `dry_run` default to
/// false. The summary comes from the first non-empty `///` doc line.
#[proc_macro_derive(Command, attributes(command))]
pub fn derive_command(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    match command::expand(&input) {
        Ok(ts) => ts.into(),
        Err(e) => e.write_errors().into(),
    }
}

/// Derive `gob_directives::Directive`, a `DirectiveMeta` and an inventory entry.
///
/// Struct attribute `#[directive(namespace = "frob", verb = "ticket")]`; field
/// attributes `#[arg(positional)]` (the default), `#[arg(key = "because")]`,
/// `#[arg(list)]` (a `Vec<T>` taking the remaining positionals), plus
/// `optional` (needs `Option<T>`) and `ticket_ref` (value is a ticket id).
/// The summary comes from the first non-empty `///` doc line.
#[proc_macro_derive(Directive, attributes(directive, arg))]
pub fn derive_directive(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    match directive::expand(&input) {
        Ok(ts) => ts.into(),
        Err(e) => e.write_errors().into(),
    }
}
