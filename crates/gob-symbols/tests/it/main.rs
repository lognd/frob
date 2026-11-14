//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M4CTE9W9QH6SBZSJ3E0E8M28
mod api_surface;
mod c_java_calls;
mod call_edges;
mod cicd;
mod corpus;
mod crosscrate;
mod csharp;
mod csharp_fixtures;
mod css;
mod def_use;
mod doc_claims;
mod dotnet;
mod dynamic_code;
mod gaps;
mod html;
mod inference;
mod link_cache;
mod measured;
mod name_lookups;
mod nodejs;
mod python;
mod python_types;
mod scss;
mod symbolic_guard;
mod symbols;
mod typescript;
mod typescript_consteval;
mod typescript_exports;
mod typescript_inherit;
mod typescript_types;
mod unity_project;
mod uss;
mod web_corpus;

/// The UTF-8 text of the file at `p`; tests want a loud failure, not a `Result`.
pub(crate) fn slurp(p: &std::path::Path) -> String {
    std::fs::read_to_string(p).expect("read")
}
