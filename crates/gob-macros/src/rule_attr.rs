//! The `#[rule(..)]` attribute of rule-authoring.md (D107, ~N88H9SY; spiked in ~9R52NCF).
//!
//! Every field is required. The colocated `<stem>.md` is read at expansion and `include_str!`d.
//! The expansion targets `::gob_rules` (`RuleDef`, `RuleDecl`, the evaluation traits) and its
//! re-export of `gob-caps`, whose matrix the compile-time asserts read. The old
//! `#[derive(Rule)]` is separate and deprecated.

use proc_macro2::{Span, TokenStream};
use quote::{quote, quote_spanned};
use syn::parse::{Parse, ParseStream};
use syn::spanned::Spanned;
use syn::{Ident, ItemStruct, Lit, LitStr, Token, bracketed, parenthesized};

use crate::{rule_doc, valid_id, valid_slug};

const SEVERITY: &[&str] = &["Error", "Warn", "Advisory"];
const POLARITY: &[&str] = &["Pplus", "Pminus", "P0", "Pn", "Pc"];
const SCOPE: &[&str] = &["File", "Repo"];
const FIX: &[&str] = &["Manual", "Deterministic", "VerifyCommit", "FixIt"];
const REQUIRED: &[&str] = &[
    "id",
    "slug",
    "severity",
    "polarity",
    "must_measure",
    "scope",
    "fix",
    "applies",
    "host",
    "version",
    "since",
];
const RT: &str = "::gob_rules";
const MATRIX_PATH: &str = "crates/gob-caps/src/matrix.rs";

/// How a rule says which files it applies to (`applies = ..`).
enum Applies {
    Universal(Tail),
    Languages(Vec<Ident>, Tail),
    Project,
}

/// The shared `needs = [..], min_fidelity = F` tail of `universal` and `languages`.
struct Tail {
    needs: Vec<Ident>,
    min_fidelity: Option<Ident>,
}

/// One parsed `key = value` argument.
enum Value {
    Ident(Ident),
    Lit(Lit),
    Applies(Applies),
}

/// All `key = value` arguments of the attribute, in source order.
struct Args(Vec<(Ident, Value)>);

fn parse_tail(input: ParseStream) -> syn::Result<Tail> {
    let mut tail = Tail {
        needs: Vec::new(),
        min_fidelity: None,
    };
    let mut seen_needs = false;
    while !input.is_empty() {
        let key: Ident = input.parse()?;
        input.parse::<Token![=]>()?;
        match key.to_string().as_str() {
            "needs" => {
                let inner;
                bracketed!(inner in input);
                let list = inner.parse_terminated(Ident::parse, Token![,])?;
                tail.needs = list.into_iter().collect();
                seen_needs = true;
            }
            "min_fidelity" => tail.min_fidelity = Some(input.parse()?),
            other => {
                return Err(syn::Error::new(
                    key.span(),
                    format!("unknown applies field `{other}`; expected `needs` or `min_fidelity`"),
                ));
            }
        }
        if !input.is_empty() {
            input.parse::<Token![,]>()?;
        }
    }
    if !seen_needs {
        return Err(input.error("`applies` requires `needs = [..]` (use `needs = []` for none)"));
    }
    Ok(tail)
}

impl Parse for Applies {
    fn parse(input: ParseStream) -> syn::Result<Self> {
        let kind: Ident = input.parse()?;
        match kind.to_string().as_str() {
            "project" => Ok(Applies::Project),
            "universal" => {
                let inner;
                parenthesized!(inner in input);
                Ok(Applies::Universal(parse_tail(&inner)?))
            }
            "languages" => {
                let inner;
                parenthesized!(inner in input);
                let mut langs = Vec::new();
                while !inner.peek(Token![;]) {
                    langs.push(inner.parse::<Ident>()?);
                    if inner.peek(Token![,]) {
                        inner.parse::<Token![,]>()?;
                    } else {
                        break;
                    }
                }
                inner.parse::<Token![;]>()?;
                if langs.is_empty() {
                    return Err(syn::Error::new(
                        kind.span(),
                        "`languages(..)` names no language",
                    ));
                }
                Ok(Applies::Languages(langs, parse_tail(&inner)?))
            }
            other => Err(syn::Error::new(
                kind.span(),
                format!(
                    "unknown applies form `{other}`; expected `universal(..)`, `languages(..)` or `project`"
                ),
            )),
        }
    }
}

impl Parse for Args {
    fn parse(input: ParseStream) -> syn::Result<Self> {
        let mut out = Vec::new();
        while !input.is_empty() {
            let key: Ident = input.parse()?;
            input.parse::<Token![=]>()?;
            let value = if key == "applies" {
                Value::Applies(input.parse()?)
            } else if input.peek(Ident) {
                Value::Ident(input.parse()?)
            } else {
                Value::Lit(input.parse()?)
            };
            out.push((key, value));
            if !input.is_empty() {
                input.parse::<Token![,]>()?;
            }
        }
        Ok(Args(out))
    }
}

/// Collects errors so one run reports every problem.
#[derive(Default)]
struct Errors(Option<syn::Error>);

impl Errors {
    fn push(&mut self, e: syn::Error) {
        match &mut self.0 {
            Some(acc) => acc.combine(e),
            None => self.0 = Some(e),
        }
    }
    fn at(&mut self, span: Span, msg: impl std::fmt::Display) {
        self.push(syn::Error::new(span, msg));
    }
}

fn find<'a>(args: &'a Args, key: &str) -> Option<&'a Value> {
    args.0.iter().find(|(k, _)| k == key).map(|(_, v)| v)
}

fn string_of(args: &Args, key: &str, errs: &mut Errors) -> Option<LitStr> {
    match find(args, key)? {
        Value::Lit(Lit::Str(s)) => Some(s.clone()),
        Value::Lit(l) => {
            errs.at(l.span(), format!("`{key}` must be a string literal"));
            None
        }
        Value::Ident(i) => {
            errs.at(i.span(), format!("`{key}` must be a string literal"));
            None
        }
        Value::Applies(_) => None,
    }
}

fn choice_of(args: &Args, key: &str, allowed: &[&str], errs: &mut Errors) -> Option<Ident> {
    match find(args, key)? {
        Value::Ident(i) if allowed.iter().any(|a| i == a) => Some(i.clone()),
        Value::Ident(i) => {
            errs.at(
                i.span(),
                format!(
                    "invalid {key} `{i}`; expected one of: {}",
                    allowed.join(", ")
                ),
            );
            None
        }
        _ => {
            errs.at(
                Span::call_site(),
                format!("`{key}` must be one of: {}", allowed.join(", ")),
            );
            None
        }
    }
}

/// Parse `major.minor.patch` into numbers.
fn semver(s: &str) -> Option<(u64, u64, u64)> {
    let mut it = s.split('.');
    let v = (
        it.next()?.parse().ok()?,
        it.next()?.parse().ok()?,
        it.next()?.parse().ok()?,
    );
    it.next().is_none().then_some(v)
}

/// Resolve the rule page next to the declaring file and validate it; the include path is
/// the sibling file name, which `include_str!` resolves relative to the same source file.
fn check_page(item: &ItemStruct, id: &str, slug: &str, errs: &mut Errors) -> Option<String> {
    let span = item.ident.span();
    let file = span.unwrap().local_file();
    let Some(file) = file else {
        errs.at(
            span,
            "cannot locate the source file of this rule, so its `.md` cannot be read",
        );
        return None;
    };
    let file = std::path::absolute(&file).unwrap_or(file);
    let stem = file
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or_default()
        .to_owned();
    if stem != id.to_ascii_lowercase() {
        errs.at(
            span,
            format!("the rule file must be named `{}.rs` (found `{stem}.rs`): the file stem is the lowercase id", id.to_ascii_lowercase()),
        );
        return None;
    }
    let md_path = file.with_extension("md");
    let md = match std::fs::read_to_string(&md_path) {
        Ok(md) => md,
        Err(e) => {
            errs.at(
                span,
                format!("rule {id} has no readable page `{stem}.md` next to its source ({}); every rule needs one", io_reason(e.kind())),
            );
            return None;
        }
    };
    let problems = rule_doc::validate(&md, id, slug);
    for p in &problems {
        errs.at(span, format!("rule page `{stem}.md`: {p}"));
    }
    problems.is_empty().then(|| format!("{stem}.md"))
}

/// Maps an io error kind to a fixed phrase so diagnostics are identical on every OS.
fn io_reason(kind: std::io::ErrorKind) -> &'static str {
    use std::io::ErrorKind;
    match kind {
        ErrorKind::NotFound => "not found",
        ErrorKind::PermissionDenied => "permission denied",
        ErrorKind::InvalidData => "not valid UTF-8",
        _ => "unreadable",
    }
}

fn rt(path: &str) -> TokenStream {
    format!("{RT}::{path}").parse().unwrap_or_default()
}

fn enum_tokens(ty: &str, v: &Ident) -> TokenStream {
    let ty = rt(ty);
    quote_spanned!(v.span()=> #ty::#v)
}

fn caps_list(needs: &[Ident]) -> TokenStream {
    let cap = rt("caps::Capability");
    quote!(&[#(#cap::#needs),*])
}

/// Const asserts tying `applies` to the capability matrix, each with a literal message.
fn matrix_asserts(id: &str, a: &Applies) -> TokenStream {
    let caps = rt("caps");
    let (lang_ty, cap_ty) = (rt("caps::Lang"), rt("caps::Capability"));
    match a {
        Applies::Project => quote!(),
        Applies::Universal(t) => {
            let fid = fidelity(t);
            let list = caps_list(&t.needs);
            let names: Vec<String> = t.needs.iter().map(ToString::to_string).collect();
            let msg = format!(
                "{id}: universal rule is unsatisfiable: no language provides all of [{}] at fidelity {} or better; matrix: {MATRIX_PATH}",
                names.join(", "),
                t.min_fidelity
                    .as_ref()
                    .map_or("F1".to_owned(), ToString::to_string)
            );
            let span = t.needs.first().map_or_else(Span::call_site, Ident::span);
            quote_spanned!(span=> const _: () = assert!(#caps::universal_satisfiable(#list, #fid), #msg);)
        }
        Applies::Languages(langs, t) => {
            let fid = fidelity(t);
            let mut out = TokenStream::new();
            for l in langs {
                let msg = format!(
                    "{id}: language {l} is below the fidelity {} this rule needs; matrix: {MATRIX_PATH}",
                    t.min_fidelity
                        .as_ref()
                        .map_or("F1".to_owned(), ToString::to_string)
                );
                out.extend(quote_spanned!(l.span()=> const _: () = assert!(#caps::lang_fidelity(#lang_ty::#l) as u8 >= #fid as u8, #msg);));
                for c in &t.needs {
                    let msg = format!(
                        "{id}: language {l} has no `{c}` capability (declared not-applicable or a gap), so this rule could never fire there; matrix: {MATRIX_PATH}"
                    );
                    out.extend(quote_spanned!(c.span()=> const _: () = assert!(#caps::provides(#lang_ty::#l, #cap_ty::#c), #msg);));
                }
            }
            out
        }
    }
}

fn fidelity(t: &Tail) -> TokenStream {
    let ty = rt("caps::Fidelity");
    if let Some(f) = &t.min_fidelity {
        quote_spanned!(f.span()=> #ty::#f)
    } else {
        quote!(#ty::F1)
    }
}

fn applies_tokens(a: &Applies) -> TokenStream {
    let ty = rt("Applies");
    let lang_ty = rt("caps::Lang");
    match a {
        Applies::Project => quote!(#ty::Project),
        Applies::Universal(t) => {
            let (list, fid) = (caps_list(&t.needs), fidelity(t));
            quote!(#ty::Universal { needs: #list, min_fidelity: #fid })
        }
        Applies::Languages(langs, t) => {
            let (list, fid) = (caps_list(&t.needs), fidelity(t));
            quote!(#ty::Languages { langs: &[#(#lang_ty::#langs),*], needs: #list, min_fidelity: #fid })
        }
    }
}

/// Expand `#[rule(..)] struct X;` into `Rule` plus the compile-time checks.
// One linear validation pass over every field; splitting it would scatter the required-field list.
#[allow(clippy::too_many_lines)]
pub(crate) fn expand(attr: TokenStream, item: &ItemStruct) -> Result<TokenStream, syn::Error> {
    let mut errs = Errors::default();
    let args: Args = syn::parse2(attr)?;
    for (i, (k, _)) in args.0.iter().enumerate() {
        if !REQUIRED.contains(&k.to_string().as_str()) {
            errs.at(
                k.span(),
                format!(
                    "unknown rule field `{k}`; fields are: {}",
                    REQUIRED.join(", ")
                ),
            );
        }
        if args.0[..i].iter().any(|(p, _)| p == k) {
            errs.at(k.span(), format!("duplicate rule field `{k}`"));
        }
    }
    for r in REQUIRED {
        if find(&args, r).is_none() {
            errs.at(
                Span::call_site(),
                format!("#[rule] is missing the required field `{r}` (every field is required)"),
            );
        }
    }
    if !matches!(item.fields, syn::Fields::Unit) {
        errs.at(item.fields.span(), "#[rule] goes on a unit struct");
    }
    if !item.generics.params.is_empty() {
        errs.at(
            item.generics.span(),
            "#[rule] does not support generic types",
        );
    }

    let id = string_of(&args, "id", &mut errs);
    let slug = string_of(&args, "slug", &mut errs);
    let since = string_of(&args, "since", &mut errs);
    if let Some(id) = &id
        && valid_id(&id.value()).is_none()
    {
        errs.at(id.span(), format!("invalid rule id `{}`; expected FAMILY (2-8 uppercase letters) + 3 digits, e.g. COV006", id.value()));
    }
    if let Some(s) = &slug
        && !valid_slug(&s.value())
    {
        errs.at(
            s.span(),
            format!(
                "invalid slug `{}`; expected lowercase kebab-case",
                s.value()
            ),
        );
    }
    if let Some(s) = &since {
        let pkg = std::env::var("CARGO_PKG_VERSION").unwrap_or_default();
        let cur = semver(&pkg);
        match (semver(&s.value()), cur) {
            (None, _) => errs.at(
                s.span(),
                format!("`since` must be a semver `x.y.z`, got `{}`", s.value()),
            ),
            (Some(v), Some(c)) if v > c => errs.at(
                s.span(),
                format!(
                    "`since = \"{}\"` is in the future (this crate is {pkg})",
                    s.value()
                ),
            ),
            _ => {}
        }
    }
    let version = match find(&args, "version") {
        Some(Value::Lit(Lit::Int(n))) => match n.base10_parse::<u32>() {
            Ok(0) => {
                errs.at(n.span(), "`version` must be at least 1");
                None
            }
            Ok(v) => Some(v),
            Err(e) => {
                errs.push(e);
                None
            }
        },
        Some(_) => {
            errs.at(Span::call_site(), "`version` must be an integer literal");
            None
        }
        None => None,
    };
    let must_measure = match find(&args, "must_measure") {
        Some(Value::Lit(Lit::Bool(b))) => Some(b.value),
        Some(_) => {
            errs.at(
                Span::call_site(),
                "`must_measure` must be `true` or `false`",
            );
            None
        }
        None => None,
    };
    let host = match find(&args, "host") {
        Some(Value::Ident(i)) => Some(i.clone()),
        Some(_) => {
            errs.at(
                Span::call_site(),
                "`host` must name the host trait the rule evaluates against",
            );
            None
        }
        None => None,
    };
    let severity = choice_of(&args, "severity", SEVERITY, &mut errs);
    let polarity = choice_of(&args, "polarity", POLARITY, &mut errs);
    let scope = choice_of(&args, "scope", SCOPE, &mut errs);
    let fix = choice_of(&args, "fix", FIX, &mut errs);
    let applies = match find(&args, "applies") {
        Some(Value::Applies(a)) => Some(a),
        _ => None,
    };
    // A malformed id or slug already has its own error; do not pile a page error on top.
    let page = match (&id, &slug) {
        (Some(i), Some(s)) if valid_id(&i.value()).is_some() && valid_slug(&s.value()) => {
            check_page(item, &i.value(), &s.value(), &mut errs)
        }
        _ => None,
    };

    if let Some(e) = errs.0 {
        return Err(e);
    }
    let (Some(id), Some(slug), Some(since), Some(version), Some(must_measure), Some(host)) =
        (id, slug, since, version, must_measure, host)
    else {
        unreachable!("all fields validated above");
    };
    let (Some(severity), Some(polarity), Some(scope), Some(fix), Some(applies), Some(page)) =
        (severity, polarity, scope, fix, applies, page)
    else {
        unreachable!("all fields validated above");
    };

    let name = &item.ident;
    let family = crate::valid_id(&id.value()).unwrap_or_default().to_owned();
    let rule_ty = rt("RuleDecl");
    let def_ty = rt("RuleDef");
    let (sev, pol, sc, fx) = (
        enum_tokens("Severity", &severity),
        enum_tokens("Polarity", &polarity),
        enum_tokens("Scope", &scope),
        enum_tokens("FixKind", &fix),
    );
    let applies_ts = applies_tokens(applies);
    let asserts = matrix_asserts(&id.value(), applies);
    let host_span = host.span();
    let eval_trait = rt(if scope == "File" {
        "FileRule"
    } else {
        "RepoRule"
    });
    let measured = rt("Measured");
    let probe = quote_spanned!(host_span=>
        const _: () = {
            fn need<P: ?Sized, R: #eval_trait<P>>() {}
            let _ = need::<dyn #host, #name>;
        };
    );
    let measure_probe = if must_measure {
        quote_spanned!(host_span=>
            const _: () = {
                fn need<P: ?Sized, R: #measured<P>>() {}
                let _ = need::<dyn #host, #name>;
            };
        )
    } else {
        quote!()
    };
    Ok(quote! {
        #item
        impl #rule_ty for #name {
            const DEF: &'static #def_ty = &#def_ty {
                id: #id,
                slug: #slug,
                family: #family,
                severity: #sev,
                polarity: #pol,
                must_measure: #must_measure,
                scope: #sc,
                fix: #fx,
                applies: #applies_ts,
                version: #version,
                since: #since,
                doc: include_str!(#page),
                file: ::core::file!(),
                line: ::core::line!(),
            };
        }
        #asserts
        #probe
        #measure_probe
    })
}
