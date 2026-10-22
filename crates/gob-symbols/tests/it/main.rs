//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M4CTE9W9QH6SBZSJ3E0E8M28
mod call_edges;
mod cicd;
mod corpus;
mod crosscrate;
mod csharp;
mod csharp_fixtures;
mod css;
mod def_use;
mod dotnet;
mod gaps;
mod html;
mod inference;
mod link_cache;
mod measured;
mod nodejs;
mod python;
mod python_types;
mod symbols;
mod typescript;
mod typescript_consteval;
mod typescript_types;
mod unity_project;
mod web_corpus;
