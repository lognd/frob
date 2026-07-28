//! Lexer + recursive-descent parser for the strata surface grammar v0
//! (docs/strata/surface.md#parser). Deterministic and fuzz-safe: every
//! malformed input yields an `err` JSON object with line/col instead of
//! panicking (charter D3 as amended: the parser is compute-heavy and
//! lives here; Python only calls `parse_source` and validates the JSON
//! into pydantic AST models).
//!
//! This module is the parser spine only: the grammar itself is split by
//! family into sibling modules (T-1099, splitting the former 4346-line
//! single-file `parse.rs`) --
//! - `lexer`: tokenizer (`Token`/`TokKind`/`ParseError`/`lex`)
//! - `grammar_core`: `Parser`/`ModuleAst` definitions and shared
//!   token-stream primitives every grammar family builds on
//! - `grammar_node`: `node`/`secret`/`on_deploy` productions
//! - `grammar_flow`: `flow`/`boundary`/`operation`/`refine` productions
//! - `grammar_infra`: `store`/`cache`/`resource`/`queue`/`cdn`/`balancer`
//!   productions
//! - `grammar_policy`: `policy`/`claim`/`scenario` productions and the
//!   top-level `parse_program` entry point
//!
//! Every grammar-family fragment contributes its own `impl Parser { ... }`
//! block, spliced into THIS module's scope via `include!` (textual
//! inclusion, not a real `mod`) rather than declared as separate `mod`
//! items -- deliberately: `Parser`/`ModuleAst`/`Token`/`ParseError` and
//! every helper method stay exactly as private as they were in the
//! pre-split monolithic file (a real child `mod` would force `pub(crate)`
//! visibility on all of it purely to let sibling grammar-family modules
//! reach the shared `Parser` surface, which would misrepresent ~50
//! internal recursive-descent helpers as this crate's public API and
//! spuriously demand a `frob:doc`/`frob:tests` edge on each one). The only
//! symbol this module actually exports to `lib.rs` is `parse_source_impl`
//! -- the public JSON surface is unchanged, byte-identical to the
//! pre-split behavior.
// frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
// strata-core/src/parse.rs's exclusivity-vocabulary hit is source-level \
// design-rationale/scope-cut prose (a docstring or comment describing \
// already-implemented internal behavior, verifiable by reading the code it annotates) \
// rather than a separate cross-module contract needing its own tracked invariant; \
// disposed as a calibration batch, not claim-by-claim. Preserved verbatim across \
// the T-1099 module split so the waived line's rationale still applies to the \
// (now-relocated) parser spine."

use serde::Serialize;
use serde_json::json;

include!("lexer.rs");
include!("grammar_core.rs");
include!("grammar_node.rs");
include!("grammar_flow.rs");
include!("grammar_infra.rs");
include!("grammar_policy.rs");

/// Parse strata surface source text into a JSON-encoded AST or diagnostic.
///
/// WHY: the parser is compute-heavy (charter D3, amended 2026-07-17) so it
/// lives in Rust; JSON is the narrowest possible interface back to Python,
/// keeping the grammar's only home in this file instead of duplicated in
/// pydantic validators.
pub(crate) fn parse_source_impl(text: &str) -> String {
    // frob:doc docs/strata/surface.md#parser
    // frob:tests strata-core/src/parse/mod.rs::parse_source_impl kind="unit"
    // frob:waive AFFECT001 reason="T-1099 pure file-relocation refactor: the \
    // diff moves this function's body verbatim from parse.rs to parse/mod.rs \
    // (git sees the whole file as new, so the body reads as changed), no \
    // grammar/JSON-surface behavior changed; docs/strata/surface.md#parser's \
    // prose still accurately describes the unchanged behavior -- cargo tests \
    // (137 passing, unchanged) are this refactor's safety net, not a doc edit"
    match lex(text).and_then(|toks| Parser::new(toks).parse_program()) {
        Ok(module) => json!({ "ok": module }).to_string(),
        Err(e) => json!({
            "err": {"line": e.line, "col": e.col, "message": e.message}
        })
        .to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn ok(text: &str) -> Value {
        let s = parse_source_impl(text);
        let v: Value = serde_json::from_str(&s).unwrap();
        v.get("ok")
            .unwrap_or_else(|| panic!("expected ok, got {}", s))
            .clone()
    }

    fn err(text: &str) -> Value {
        let s = parse_source_impl(text);
        let v: Value = serde_json::from_str(&s).unwrap();
        v.get("err")
            .unwrap_or_else(|| panic!("expected err, got {}", s))
            .clone()
    }

    #[test]
    // frob:ticket T-0148
    fn parses_bare_module() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // frob:tests strata-core/src/parse/mod.rs::parse_source_impl kind="unit"
        let v = ok("module payments");
        assert_eq!(v["name"], "payments");
        assert_eq!(v["nodes"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_node_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node api : trusted abstract {
                clearance Secret;
                attr idempotent;
                attr region=us;
                residence us_east;
                capacity 100 req/s replicas 1..8;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["id"], "api");
        assert_eq!(n["trust"], "trusted");
        assert_eq!(n["is_abstract"], true);
        assert_eq!(n["clearance"], "Secret");
        assert_eq!(n["attrs"][0], "idempotent");
        assert_eq!(n["attrs"][1], "region=us");
        assert_eq!(n["residence"], "us_east");
        assert_eq!(n["capacity"]["rate"]["value"], 100.0);
        assert_eq!(n["capacity"]["rate"]["unit"], "req/s");
        assert_eq!(n["capacity"]["replicas_min"], 1);
        assert_eq!(n["capacity"]["replicas_max"], 8);
    }

    #[test]
    fn parses_flow_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            flow f1 : a -> b {
                label Pii;
                age 250 ms;
                rate 5 req/s;
                size 4 KiB;
                attr delivery=at_least_once;
                transport tls;
            }"#);
        let f = &v["flows"][0];
        assert_eq!(f["src"], "a");
        assert_eq!(f["dst"], "b");
        assert_eq!(f["label"], "Pii");
        assert_eq!(f["age"]["value"], 250.0);
        assert_eq!(f["age"]["unit"], "ms");
        assert_eq!(f["rate"]["unit"], "req/s");
        assert_eq!(f["size"]["unit"], "KiB");
        assert_eq!(f["attrs"][0], "delivery=at_least_once");
        assert_eq!(f["transport"][0], "tls");
    }

    #[test]
    fn parses_percent_unit() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            assert c1 bound utilization api <= 80 %"#);
        assert_eq!(v["claims"][0]["limit"]["unit"], "%");
    }

    #[test]
    fn parses_boundary() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified""#);
        let b = &v["boundaries"][0];
        assert_eq!(b["kind"], "endorse");
        assert_eq!(b["flow_id"], "f1");
        assert_eq!(b["from_level"], "foreign");
        assert_eq!(b["to_level"], "authenticated");
        assert_eq!(b["predicate"], "jwt_verified");
    }

    #[test]
    fn parses_assert_noflow_and_reach() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            assert c1 noflow evil -> api
            assert c2 reach audit -> log"#);
        assert_eq!(v["claims"][0]["kind"], "noflow");
        assert_eq!(v["claims"][1]["kind"], "reach");
    }

    #[test]
    fn parses_assume_with_owner_and_review() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            assume c1 noflow evil -> api owner alice review "2026-08-01""#);
        assert_eq!(v["claims"][0]["assumed"], true);
        assert_eq!(v["claims"][0]["owner"], "alice");
        assert_eq!(v["claims"][0]["review"], "2026-08-01");
    }

    #[test]
    fn parses_string_quoted_claim_id() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: a discharge claim id naming a catalog obligation
        // ("weakness:CWE-79:web") cannot lex as IDENT ('-'/':' are not
        // ident chars) -- the claim-id position also accepts a
        // STRING-quoted id.
        let v = ok(r#"module m
            assert "weakness:CWE-79:web" noflow evil -> api"#);
        assert_eq!(v["claims"][0]["id"], "weakness:CWE-79:web");
        assert_eq!(v["claims"][0]["kind"], "noflow");
    }

    #[test]
    fn parses_string_quoted_claim_id_on_assume() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: quoted claim id alongside the owner/review assume tail.
        let v = ok(r#"module m
            assume "weakness:CWE-89:web" noflow evil -> api owner alice review "2026-08-01""#);
        assert_eq!(v["claims"][0]["id"], "weakness:CWE-89:web");
        assert_eq!(v["claims"][0]["assumed"], true);
        assert_eq!(v["claims"][0]["owner"], "alice");
        assert_eq!(v["claims"][0]["review"], "2026-08-01");
    }

    #[test]
    fn bare_ident_claim_id_still_parses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: the pre-existing bare-IDENT claim id form must keep
        // working unchanged alongside the new quoted alternate.
        let v = ok(r#"module m
            assert c1 noflow evil -> api"#);
        assert_eq!(v["claims"][0]["id"], "c1");
    }

    #[test]
    fn error_unterminated_string_claim_id() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: an unterminated string in the claim-id position fails
        // at the lexer with a real line/col, not a silent misparse.
        let e = err("module m\nassert \"weakness:CWE-79:web noflow evil -> api");
        assert_eq!(e["line"], 2);
        assert!(e["message"].as_str().unwrap().contains("string"));
    }

    #[test]
    fn error_malformed_claim_id_neither_ident_nor_string() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0138: a claim id that is neither IDENT nor STRING (e.g. a bare
        // number) is still a parse error at the claim-id position.
        let e = err("module m\nassert 123 noflow evil -> api");
        assert_eq!(e["message"], "expected claim id");
        assert_eq!(e["line"], 2);
    }

    #[test]
    fn parses_node_code_globs_and_may_capabilities() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: code=<glob> / may <capability> surface grammar.
        let v = ok(r#"module m
            node api : trusted {
                code "src/frob/**" "tests/frob/**";
                may "net.out:stripe.com";
                may "fs.read:/etc/tls";
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["code"][0], "src/frob/**");
        assert_eq!(n["code"][1], "tests/frob/**");
        assert_eq!(n["may"][0], "net.out:stripe.com");
        assert_eq!(n["may"][1], "fs.read:/etc/tls");
    }

    #[test]
    fn parses_node_without_code_or_may_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: pre-existing sources with no code/may statements must
        // still elaborate -- both fields default to an empty list.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert_eq!(n["code"].as_array().unwrap().len(), 0);
        assert_eq!(n["may"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_code_requires_at_least_one_glob() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: `code` is glob+, not glob*; a bare `code;` is a parse
        // error rather than silently binding zero globs (law 2).
        let e = err(r#"module m
            node api : trusted {
                code;
            }"#);
        assert_eq!(e["message"], "expected code glob");
    }

    #[test]
    fn error_may_requires_string_not_ident() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0132: capability atoms are STRING-quoted; a bare ident is
        // rejected rather than silently truncated at the first `.`/`:`.
        let e = err(r#"module m
            node api : trusted {
                may net.out;
            }"#);
        assert_eq!(e["message"], "expected may capability");
    }

    #[test]
    fn parses_node_carries_pii_tags() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: `carries PII_TAG+` -- one or more STRING-quoted PII tags
        // on a node, the same STRING+ shape T-0132 established for `code`.
        let v = ok(r#"module m
            node api : trusted {
                carries "identifier.email" "contact.phone";
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["carries"][0], "identifier.email");
        assert_eq!(n["carries"][1], "contact.phone");
    }

    #[test]
    fn parses_store_carries_pii_tags() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: `carries` is also legal inside `store` -- the most
        // common PII resting place.
        let v = ok(r#"module m
            store users : trusted {
                carries "identifier.email";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["carries"][0], "identifier.email");
    }

    #[test]
    fn parses_store_code_globs_and_may_capabilities() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: `code`/`may` are also legal inside `store` -- "component
        // / store: nodes" (docs/strata/surface.md#key-construct-semantics),
        // same STRING+ / STRING shape T-0132 gave `node`.
        let v = ok(r#"module m
            store tickets_ledger : trusted {
                code "src/frob/tickets/**";
                may "fs";
                may "exec";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["code"][0], "src/frob/tickets/**");
        assert_eq!(s["may"][0], "fs");
        assert_eq!(s["may"][1], "exec");
    }

    #[test]
    fn parses_store_without_code_or_may_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: pre-existing store sources with no code/may statements
        // must still elaborate -- both fields default to an empty list.
        let v = ok("module m\nstore users : trusted");
        let s = &v["stores"][0];
        assert_eq!(s["code"].as_array().unwrap().len(), 0);
        assert_eq!(s["may"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_store_code_requires_at_least_one_glob() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: `code` on a store is glob+, not glob*, same as `node`.
        let e = err(r#"module m
            store users : trusted {
                code;
            }"#);
        assert_eq!(e["message"], "expected code glob");
    }

    #[test]
    fn error_store_may_requires_string_not_ident() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0166: capability atoms on a store are STRING-quoted, same as
        // `node`; a bare ident is rejected.
        let e = err(r#"module m
            store users : trusted {
                may net.out;
            }"#);
        assert_eq!(e["message"], "expected may capability");
    }

    #[test]
    fn parses_node_without_carries_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: pre-existing sources with no `carries` statement must
        // still elaborate -- the field defaults to an empty list.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert_eq!(n["carries"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_carries_requires_at_least_one_tag() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0154: `carries` is tag+, not tag*; a bare `carries;` is a
        // parse error rather than silently binding zero tags (law 2).
        let e = err(r#"module m
            node api : trusted {
                carries;
            }"#);
        assert_eq!(e["message"], "expected carries pii tag");
    }

    #[test]
    fn parses_secret_construct() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `secret ID { issued_by ...; audience { ... }; lifetime
        // ...; revoke ... }` -- surface syntax for `_secrets.py::SecretSpec`.
        let v = ok(r#"module m
            node vault : trusted
            node api : trusted
            secret db_creds {
                issued_by vault;
                audience { api };
                lifetime 24 h;
                revoke 5 min;
            }"#);
        let s = &v["secrets"][0];
        assert_eq!(s["id"], "db_creds");
        assert_eq!(s["issued_by"], "vault");
        assert_eq!(s["audience"][0], "api");
        assert_eq!(s["lifetime"]["value"], 24.0);
        assert_eq!(s["lifetime"]["unit"], "h");
        assert_eq!(s["revoke"]["value"], 5.0);
        assert_eq!(s["revoke"]["unit"], "min");
    }

    #[test]
    fn parses_secret_without_revoke_or_audience() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `revoke`/`audience` are grammar-optional -- the mandatory-
        // revocation rule fails closed in the elaborator
        // (`_secrets.py::_validate_secret_bounds`), not the parser.
        let v = ok(r#"module m
            node vault : trusted
            secret db_creds {
                issued_by vault;
                lifetime 24 h;
            }"#);
        let s = &v["secrets"][0];
        assert_eq!(s["audience"].as_array().unwrap().len(), 0);
        assert!(s["revoke"].is_null());
    }

    #[test]
    fn error_secret_requires_issued_by() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `issued_by` is mandatory -- a credential with no named
        // issuing authority is a dangling promise, never a silent default.
        let e = err(r#"module m
            secret db_creds {
                lifetime 24 h;
            }"#);
        assert_eq!(e["message"], "secret needs an issued_by clause");
    }

    #[test]
    fn parses_on_deploy_block() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `on deploy { canary { ... }; endorsed_by ...; rollback
        // within ... }` -- surface syntax for `_models.py::DeployContract`.
        let v = ok(r#"module m
            node api : trusted {
                on deploy {
                    canary { canary for 10 min, staged for 30 min };
                    endorsed_by review_gate, build_gate;
                    rollback within 5 min;
                }
            }"#);
        let d = &v["nodes"][0]["deploy"];
        assert_eq!(d["stages"][0]["level"], "canary");
        assert_eq!(d["stages"][0]["bake"]["value"], 10.0);
        assert_eq!(d["stages"][1]["level"], "staged");
        assert_eq!(d["endorsed_by"][0], "review_gate");
        assert_eq!(d["endorsed_by"][1], "build_gate");
        assert_eq!(d["rollback_budget"]["value"], 5.0);
        assert_eq!(d["rollback_budget"]["unit"], "min");
    }

    #[test]
    fn parses_node_without_on_deploy_defaults_null() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: pre-existing sources with no `on deploy` block must still
        // elaborate -- `deploy` defaults to null (no contract declared).
        let v = ok("module m\nnode api : trusted");
        assert!(v["nodes"][0]["deploy"].is_null());
    }

    #[test]
    fn error_on_deploy_requires_rollback_budget() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0136: `rollback_budget` has no default on `DeployContract`
        // (mandatory containment bound, charter law 2) -- a deploy block
        // with no rollback clause is a parse error, not an empty default.
        let e = err(r#"module m
            node api : trusted {
                on deploy {
                    endorsed_by review_gate;
                }
            }"#);
        assert_eq!(
            e["message"],
            "on deploy block needs a rollback within QUANTITY clause"
        );
    }

    #[test]
    fn parses_node_managed_marker() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0172: `managed` is a bare marker on `node`, mirroring
        // `errors_total`'s shape -- config-only infra (e.g. a Caddyfile-
        // configured edge) declared with no `code=` glob.
        let v = ok(r#"module m
            node edge : trusted {
                managed;
            }"#);
        assert_eq!(v["nodes"][0]["is_managed"], true);
    }

    #[test]
    fn parses_node_without_managed_defaults_false() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0172: pre-existing sources with no `managed` clause must still
        // elaborate -- `is_managed` defaults to false.
        let v = ok("module m\nnode api : trusted");
        assert_eq!(v["nodes"][0]["is_managed"], false);
    }

    #[test]
    fn parses_store_managed_marker() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0172: `store` is a node too (docs/strata/surface.md
        // #key-construct-semantics) -- same bare `managed` marker.
        let v = ok(r#"module m
            store cache_db : trusted {
                managed;
            }"#);
        assert_eq!(v["stores"][0]["is_managed"], true);
    }

    #[test]
    fn parses_node_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0255: std.host vocabulary -- runs_as/unit/owns/listens on a
        // node (docs/strata/host.md).
        let v = ok(r#"module m
            node api : trusted {
                runs_as "api-svc";
                unit;
                owns "/etc/api" "0644";
                owns "/var/lib/api" "0750";
                listens 8080;
                listens 8443;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["runs_as"], "api-svc");
        assert_eq!(n["is_unit"], true);
        assert_eq!(n["owns"][0]["path"], "/etc/api");
        assert_eq!(n["owns"][0]["mode"], "0644");
        assert_eq!(n["owns"][1]["path"], "/var/lib/api");
        assert_eq!(n["owns"][1]["mode"], "0750");
        assert_eq!(n["listens"][0], 8080);
        assert_eq!(n["listens"][1], 8443);
    }

    #[test]
    fn parses_node_without_host_manifest_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0255: pre-existing sources with no std.host clause must still
        // elaborate -- runs_as null, is_unit false, owns/listens empty.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert!(n["runs_as"].is_null());
        assert_eq!(n["is_unit"], false);
        assert_eq!(n["owns"].as_array().unwrap().len(), 0);
        assert_eq!(n["listens"].as_array().unwrap().len(), 0);
        assert_eq!(n["group"].as_array().unwrap().len(), 0);
        assert_eq!(n["sudoers"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_node_group_and_sudoers_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0272: std.host OS-group and sudoers-grant vocabulary on a node
        // (docs/strata/host.md) -- HOST001's shared-group and HOST002's
        // sudoers sub-targets read these back instead of always firing.
        let v = ok(r#"module m
            node api : trusted {
                runs_as "api-svc";
                group "deploy";
                group "docker";
                sudoers "ALL=(root) NOPASSWD: /bin/systemctl restart api";
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["group"][0], "deploy");
        assert_eq!(n["group"][1], "docker");
        assert_eq!(
            n["sudoers"][0],
            "ALL=(root) NOPASSWD: /bin/systemctl restart api"
        );
    }

    #[test]
    fn parses_node_windows_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261: std.host Windows vocabulary -- platform/service_account/
        // service/acl/pipe on a node (docs/strata/host.md#windows-surface-
        // grammar).
        let v = ok(r#"module m
            node api : trusted {
                platform "windows";
                service_account "svc-api" gmsa;
                service;
                acl "C:\ProgramData\api" "BUILTIN\Administrators:FullControl";
                pipe "\\.\pipe\api-control";
                listens 8443;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["platform"], "windows");
        assert_eq!(n["service_account"], "svc-api");
        assert_eq!(n["service_account_gmsa"], true);
        assert_eq!(n["is_service"], true);
        assert_eq!(n["acl"][0]["path"], "C:\\ProgramData\\api");
        assert_eq!(n["acl"][0]["rule"], "BUILTIN\\Administrators:FullControl");
        assert_eq!(n["pipes"][0], "\\\\.\\pipe\\api-control");
        assert_eq!(n["listens"][0], 8443);
    }

    #[test]
    fn parses_node_bin_path_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0629: `bin_path "PATH" ["ARGS"]` desugars straight to
        // `bin_path=<path>` (+ `bin_path_args=<args>`) node attrs.
        let v = ok(r#"module m
            node api : trusted {
                platform "windows";
                service;
                bin_path "C:\Program Files\api\api.exe" "--config C:\ProgramData\api\config.yaml";
            }"#);
        let n = &v["nodes"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"bin_path=C:\\Program Files\\api\\api.exe"));
        assert!(attrs.contains(&"bin_path_args=--config C:\\ProgramData\\api\\config.yaml"));
    }

    #[test]
    fn parses_node_bin_path_clause_without_args() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0629: ARGS is optional -- `bin_path_args` is absent when omitted.
        let v = ok(r#"module m
            node api : trusted {
                platform "windows";
                service;
                bin_path "C:\Program Files\api\api.exe";
            }"#);
        let n = &v["nodes"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"bin_path=C:\\Program Files\\api\\api.exe"));
        assert!(!attrs.iter().any(|a| a.starts_with("bin_path_args=")));
    }

    #[test]
    fn parses_store_bin_path_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0629: `store` accepts the identical `bin_path` clause -- a
        // store is a node too.
        let v = ok(r#"module m
            store api_svc : trusted {
                platform "windows";
                service;
                bin_path "C:\Program Files\api\api.exe" "--serve";
            }"#);
        let n = &v["stores"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"bin_path=C:\\Program Files\\api\\api.exe"));
        assert!(attrs.contains(&"bin_path_args=--serve"));
    }

    #[test]
    fn parses_node_without_windows_host_manifest_defaults_empty() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261: pre-existing sources with no Windows std.host clause
        // must still elaborate -- platform/service_account null,
        // service_account_gmsa/is_service false, acl/pipes empty.
        let v = ok("module m\nnode api : trusted");
        let n = &v["nodes"][0];
        assert!(n["platform"].is_null());
        assert!(n["service_account"].is_null());
        assert_eq!(n["service_account_gmsa"], false);
        assert_eq!(n["is_service"], false);
        assert_eq!(n["acl"].as_array().unwrap().len(), 0);
        assert_eq!(n["pipes"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_store_windows_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261: same Windows std.host vocabulary on `store` -- a store
        // is a node too (docs/strata/surface.md#key-construct-semantics).
        let v = ok(r#"module m
            store cache_db : trusted {
                platform "windows";
                service_account "svc-cache";
                service;
                acl "D:\data\cache" "svc-cache:Modify";
                pipe "\\.\pipe\cache-control";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["platform"], "windows");
        assert_eq!(s["service_account"], "svc-cache");
        assert_eq!(s["service_account_gmsa"], false);
        assert_eq!(s["is_service"], true);
        assert_eq!(s["acl"][0]["path"], "D:\\data\\cache");
        assert_eq!(s["acl"][0]["rule"], "svc-cache:Modify");
        assert_eq!(s["pipes"][0], "\\\\.\\pipe\\cache-control");
    }

    #[test]
    fn parses_store_host_manifest_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0255: same std.host vocabulary on `store` -- a store is a
        // node too (docs/strata/surface.md#key-construct-semantics).
        let v = ok(r#"module m
            store cache_db : trusted {
                runs_as "cache-svc";
                unit;
                owns "/var/lib/cache_db" "0700";
                listens 6379;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["runs_as"], "cache-svc");
        assert_eq!(s["is_unit"], true);
        assert_eq!(s["owns"][0]["path"], "/var/lib/cache_db");
        assert_eq!(s["owns"][0]["mode"], "0700");
        assert_eq!(s["listens"][0], 6379);
        assert_eq!(s["group"].as_array().unwrap().len(), 0);
        assert_eq!(s["sudoers"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_store_group_and_sudoers_clauses() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0272: same `group`/`sudoers` shape as `node`'s clauses on a
        // `store` -- a store is a node too.
        let v = ok(r#"module m
            store cache_db : trusted {
                runs_as "cache-svc";
                group "dba";
                sudoers "cache-svc ALL=(root) /usr/bin/systemctl restart cache_db";
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["group"][0], "dba");
        assert_eq!(
            s["sudoers"][0],
            "cache-svc ALL=(root) /usr/bin/systemctl restart cache_db"
        );
    }

    #[test]
    fn error_module_missing() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("node a : trusted");
        assert_eq!(e["message"], "statement before module declaration");
    }

    #[test]
    fn error_duplicate_module() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nmodule b");
        assert_eq!(e["message"], "duplicate module statement");
        assert_eq!(e["line"], 2);
        assert_eq!(e["col"], 1);
    }

    #[test]
    fn error_unknown_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nbogus x");
        assert_eq!(e["message"], "unknown keyword \"bogus\"");
        assert_eq!(e["line"], 2);
        assert_eq!(e["col"], 1);
    }

    #[test]
    fn error_unknown_node_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nnode n : trusted { bogus x; }");
        assert_eq!(e["message"], "unknown node property");
    }

    #[test]
    fn error_unknown_metric() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nassert c1 bound zorp x <= 1 s");
        assert!(e["message"].as_str().unwrap().contains("unknown metric"));
    }

    #[test]
    fn error_on_empty_input_never_panics() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("");
        assert_eq!(e["message"], "missing module statement");
    }

    #[test]
    fn error_reports_accurate_line_col() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module a\nnode n : trusted {\n  clearance ;\n}");
        assert_eq!(e["line"], 3);
    }

    #[test]
    fn unit_slash_continues_but_stops_at_bare_ident() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nflow f1 : a -> b { rate 5 req/s; }");
        assert_eq!(v["flows"][0]["rate"]["unit"], "req/s");
        let v2 = ok("module m\nnode n : trusted { capacity 1 min replicas 1..1; }");
        assert_eq!(v2["nodes"][0]["capacity"]["rate"]["unit"], "min");
    }

    #[test]
    fn round_trip_small_design() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module payments
            node api : trusted { clearance Pii; capacity 100 req/s replicas 1..8; }
            node evil : foreign
            flow f1 : evil -> api { label Pii; rate 5 req/s; transport tls; }
            boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"
            assert c1 noflow evil -> api
            assume c2 bound age api <= 30 s owner alice review "2026-09-01""#);
        assert_eq!(v["nodes"].as_array().unwrap().len(), 2);
        assert_eq!(v["flows"].as_array().unwrap().len(), 1);
        assert_eq!(v["boundaries"].as_array().unwrap().len(), 1);
        assert_eq!(v["claims"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn parses_refine_happy_path() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
                flow f1 : inner -> inner
                binds api = inner
            }"#);
        let r = &v["refines"][0];
        assert_eq!(r["target"], "api");
        assert_eq!(r["bind_to"], "inner");
        assert_eq!(r["nodes"][0]["id"], "inner");
        assert_eq!(r["flows"][0]["id"], "f1");
    }

    #[test]
    fn error_refine_zero_binds() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
            }"#);
        assert_eq!(e["message"], "refine block needs exactly one binds clause");
    }

    #[test]
    fn error_refine_two_binds() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
                binds api = inner
                binds api = inner
            }"#);
        assert_eq!(e["message"], "refine block needs exactly one binds clause");
    }

    #[test]
    fn error_refine_binds_lhs_mismatch() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node api : trusted abstract
            refine api into {
                node inner : trusted
                binds wrong = inner
            }"#);
        assert!(e["message"]
            .as_str()
            .unwrap()
            .contains("must equal refine target"));
    }

    #[test]
    fn error_refine_before_module() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("refine api into { binds api = inner }");
        assert_eq!(e["message"], "statement before module declaration");
    }

    #[test]
    fn parses_store_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                clearance Pii;
                attr region=us;
                residence us_east;
                capacity 100 req/s replicas 1..4;
                engine postgres;
                immutable;
                append_only;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["id"], "db");
        assert_eq!(s["trust"], "trusted");
        assert_eq!(s["clearance"], "Pii");
        assert_eq!(s["attrs"][0], "region=us");
        assert_eq!(s["residence"], "us_east");
        assert_eq!(s["capacity"]["replicas_max"], 4);
        assert_eq!(s["engine"], "postgres");
        assert_eq!(s["immutable"], true);
        assert_eq!(s["append_only"], true);
    }

    #[test]
    fn parses_store_rpo() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                rpo 5 min;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["rpo"]["value"], 5.0);
        assert_eq!(s["rpo"]["unit"], "min");
    }

    #[test]
    fn parses_bare_store() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nstore db : trusted");
        let s = &v["stores"][0];
        assert_eq!(s["engine"], serde_json::Value::Null);
        assert_eq!(s["immutable"], false);
        assert_eq!(s["append_only"], false);
        assert_eq!(s["errors_total"], false);
        assert_eq!(s["panics_contained_by"], serde_json::Value::Null);
        assert_eq!(s["observe"], serde_json::Value::Null);
        assert_eq!(s["deploy"], serde_json::Value::Null);
    }

    #[test]
    fn parses_store_errors_total_panics_and_observe() {
        // T-0247: store_prop now accepts the same errors_total/
        // panics_contained_by/observe node_prop entries `node` has.
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                errors_total;
                panics_contained_by supervisor;
                observe { log error_paths, crash_events; to obs_sink }
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["errors_total"], true);
        assert_eq!(s["panics_contained_by"], "supervisor");
        assert_eq!(s["observe"]["log"][0], "error_paths");
        assert_eq!(s["observe"]["log"][1], "crash_events");
        assert_eq!(s["observe"]["to"], "obs_sink");
    }

    #[test]
    fn parses_store_on_deploy() {
        // T-0247: store_prop now accepts the same `on deploy { ... }`
        // node_prop entry `node` has.
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            store db : trusted {
                on deploy {
                    canary { authenticated for 10 min };
                    endorsed_by review_gate;
                    rollback within 5 min;
                }
            }"#);
        let d = &v["stores"][0]["deploy"];
        assert_eq!(d["stages"][0]["level"], "authenticated");
        assert_eq!(d["endorsed_by"][0], "review_gate");
        assert_eq!(d["rollback_budget"]["value"], 5.0);
    }

    #[test]
    fn error_store_observe_unknown_log_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nstore db : trusted { observe { bogus x; } }");
        assert_eq!(e["message"], "unknown observe property");
    }

    #[test]
    fn error_unknown_store_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nstore db : trusted { bogus x; }");
        assert_eq!(e["message"], "unknown store property");
    }

    #[test]
    fn parses_cache_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            cache c of db {
                keyed_by user_id;
                staleness 30 s;
                hit 90 %;
                policy lru;
                invalidate_on f1;
                invalidate_on f2;
            }"#);
        let c = &v["caches"][0];
        assert_eq!(c["id"], "c");
        assert_eq!(c["of"], "db");
        assert_eq!(c["keyed_by"], "user_id");
        assert_eq!(c["staleness"]["value"], 30.0);
        assert_eq!(c["staleness"]["unit"], "s");
        assert_eq!(c["hit"], 90.0);
        assert_eq!(c["policy"], "lru");
        assert_eq!(c["invalidate_on"][0], "f1");
        assert_eq!(c["invalidate_on"][1], "f2");
    }

    #[test]
    fn parses_cache_ttl() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\ncache c of db { ttl 60 s; }");
        assert_eq!(v["caches"][0]["ttl"]["value"], 60.0);
    }

    #[test]
    fn error_unknown_cache_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\ncache c of db { bogus x; }");
        assert_eq!(e["message"], "unknown cache property");
    }

    #[test]
    fn parses_queue_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            queue q {
                delivery at_least_once;
                ordering fifo;
                attr region=us;
                clearance Internal;
            }"#);
        let q = &v["queues"][0];
        assert_eq!(q["id"], "q");
        assert_eq!(q["delivery"], "at_least_once");
        assert_eq!(q["ordering"], "fifo");
        assert_eq!(q["attrs"][0], "region=us");
        assert_eq!(q["clearance"], "Internal");
    }

    #[test]
    fn error_unknown_queue_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nqueue q { bogus x; }");
        assert_eq!(e["message"], "unknown queue property");
    }

    #[test]
    fn parses_queue_with_explicit_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0093: queue may now declare an explicit TRUST clause.
        let v = ok("module m\nqueue q : authenticated { delivery at_least_once; }");
        let q = &v["queues"][0];
        assert_eq!(q["id"], "q");
        assert_eq!(q["trust"], "authenticated");
        assert_eq!(q["delivery"], "at_least_once");
    }

    #[test]
    fn parses_queue_without_trust_defaults_to_null() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0093: omitting TRUST keeps parsing (backward compatible); the
        // elaborator (not the parser) supplies the "trusted" default.
        let v = ok("module m\nqueue q { delivery at_least_once; }");
        assert_eq!(v["queues"][0]["trust"], serde_json::Value::Null);
    }

    #[test]
    fn parses_bare_queue_with_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nqueue q : authenticated");
        assert_eq!(v["queues"][0]["trust"], "authenticated");
    }

    #[test]
    fn parses_cdn_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            cdn c of origin {
                provider fastly : authenticated;
                staleness 5 min;
                hit 95 %;
                tls_terminates_at_provider;
            }"#);
        let c = &v["cdns"][0];
        assert_eq!(c["id"], "c");
        assert_eq!(c["of"], "origin");
        assert_eq!(c["provider"], "fastly");
        assert_eq!(c["provider_trust"], "authenticated");
        assert_eq!(c["staleness"]["value"], 5.0);
        assert_eq!(c["staleness_unlimited"], false);
        assert_eq!(c["hit"], 95.0);
        assert_eq!(c["tls_terminates_at_provider"], true);
    }

    #[test]
    fn parses_cdn_unlimited_staleness() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            cdn c of origin { provider fastly : authenticated; staleness unlimited; }"#);
        assert_eq!(v["cdns"][0]["staleness_unlimited"], true);
        assert_eq!(v["cdns"][0]["staleness"], serde_json::Value::Null);
    }

    #[test]
    fn error_unknown_cdn_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\ncdn c of origin { bogus x; }");
        assert_eq!(e["message"], "unknown cdn property");
    }

    #[test]
    fn parses_balancer_with_all_properties() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nbalancer b { policy round_robin; sticky; }");
        let b = &v["balancers"][0];
        assert_eq!(b["id"], "b");
        assert_eq!(b["policy"], "round_robin");
        assert_eq!(b["sticky"], true);
    }

    #[test]
    fn parses_bare_balancer() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nbalancer b");
        assert_eq!(v["balancers"][0]["policy"], serde_json::Value::Null);
        assert_eq!(v["balancers"][0]["sticky"], false);
        assert_eq!(v["balancers"][0]["trust"], serde_json::Value::Null);
    }

    #[test]
    fn parses_balancer_with_explicit_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0093: balancer may now declare an explicit TRUST clause.
        let v = ok("module m\nbalancer b : authenticated { policy round_robin; }");
        let b = &v["balancers"][0];
        assert_eq!(b["id"], "b");
        assert_eq!(b["trust"], "authenticated");
        assert_eq!(b["policy"], "round_robin");
    }

    #[test]
    fn parses_bare_balancer_with_trust() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nbalancer b : authenticated");
        assert_eq!(v["balancers"][0]["trust"], "authenticated");
    }

    #[test]
    fn parses_node_skew() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nnode n : trusted { skew zipf 1.2; }");
        assert_eq!(v["nodes"][0]["attrs"][0], "skew=1.2");
    }

    #[test]
    fn parses_store_skew() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nstore db : trusted { skew zipf 0.9; }");
        assert_eq!(v["stores"][0]["attrs"][0], "skew=0.9");
    }

    #[test]
    fn parses_flow_fanout() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nflow f1 : a -> b { fanout 2.5; }");
        assert_eq!(v["flows"][0]["attrs"][0], "fanout=2.5");
    }

    #[test]
    fn parses_flow_growth() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nflow f1 : a -> b { growth 5 %; }");
        assert_eq!(v["flows"][0]["attrs"][0], "growth=5");
    }

    #[test]
    fn parses_flow_utility() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0226: `utility;` desugars to the bare flow attr "utility".
        let v = ok("module m\nflow f1 : a -> b { utility; }");
        assert_eq!(v["flows"][0]["attrs"][0], "utility");
    }

    #[test]
    fn error_skew_requires_zipf_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nnode n : trusted { skew 1.2; }");
        assert_eq!(e["message"], "expected keyword \"zipf\"");
    }

    #[test]
    fn error_growth_requires_percent() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nflow f1 : a -> b { growth 5; }");
        assert_eq!(e["message"], "expected \'%\'");
    }

    #[test]
    fn error_unknown_balancer_property() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nbalancer b { bogus x; }");
        assert_eq!(e["message"], "unknown balancer property");
    }

    #[test]
    fn parses_policy_forbid_call_and_import() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy NoDynamicCode on trust >= trusted {
                forbid call eval, exec, importlib.import_module;
                forbid import ctypes
            }"#);
        let p = &v["policies"][0];
        assert_eq!(p["id"], "NoDynamicCode");
        assert_eq!(p["scope"]["kind"], "trust");
        assert_eq!(p["scope"]["value"], "trusted");
        assert_eq!(p["rules"][0]["kind"], "forbid_call");
        assert_eq!(p["rules"][0]["idents"][2], "importlib.import_module");
        assert_eq!(p["rules"][1]["kind"], "forbid_import");
        assert_eq!(p["rules"][1]["idents"][0], "ctypes");
    }

    #[test]
    fn parses_policy_confine_use() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy DbConfine on component Api {
                confine use psycopg to "src/api/db.py"
            }"#);
        let r = &v["policies"][0]["rules"][0];
        assert_eq!(r["kind"], "confine_use");
        assert_eq!(r["ident"], "psycopg");
        assert_eq!(r["home"], "src/api/db.py");
    }

    #[test]
    fn parses_policy_at_call_require_arg() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy TimeoutRequired on component Api {
                at call subprocess.run require arg timeout
            }"#);
        let r = &v["policies"][0]["rules"][0];
        assert_eq!(r["kind"], "at_call_require_arg");
        assert_eq!(r["ident"], "subprocess.run");
        assert_eq!(r["arg"], "timeout");
    }

    #[test]
    fn parses_policy_mediate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy DbChokepoint on component Api {
                mediate db.write via "db.py::TenantScopedSession"
            }"#);
        let r = &v["policies"][0]["rules"][0];
        assert_eq!(r["kind"], "mediate");
        assert_eq!(r["ident"], "db.write");
        assert_eq!(r["mediator"], "db.py::TenantScopedSession");
    }

    #[test]
    fn parses_policy_enables_and_rationale() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy NoDynamicCode on trust >= trusted {
                forbid call eval;
                enables extraction_soundness;
                rationale "static closure requires no dynamic dispatch"
            }"#);
        let rules = v["policies"][0]["rules"].as_array().unwrap();
        assert_eq!(rules[1]["kind"], "enables");
        assert_eq!(rules[1]["atom"], "extraction_soundness");
        assert_eq!(rules[2]["kind"], "rationale");
        assert_eq!(
            rules[2]["text"],
            "static closure requires no dynamic dispatch"
        );
    }

    #[test]
    fn parses_policy_label_scope() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy NoPiiInLogs on label >= Pii {
                forbid call logging.info
            }"#);
        assert_eq!(v["policies"][0]["scope"]["kind"], "label");
        assert_eq!(v["policies"][0]["scope"]["value"], "Pii");
    }

    #[test]
    fn parses_policy_bare_no_rules() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\npolicy Empty on component Api {}");
        assert_eq!(v["policies"][0]["rules"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_policy_unknown_scope_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on bogus X { forbid call eval }");
        assert_eq!(e["message"], "expected component, trust >=, or label >= scope");
    }

    #[test]
    fn error_policy_trust_scope_missing_ge() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on trust trusted { forbid call eval }");
        assert_eq!(e["message"], "expected >=");
    }

    #[test]
    fn error_policy_unknown_rule() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on component Api { bogus x }");
        assert_eq!(e["message"], "unknown policy rule");
    }

    #[test]
    fn error_policy_forbid_missing_call_or_import() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\npolicy P on component Api { forbid eval }");
        assert_eq!(e["message"], "expected call or import after forbid");
    }

    #[test]
    fn dotted_ident_list_round_trips_multiple_dots() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            policy P on component Api {
                forbid call a.b.c, d
            }"#);
        let idents = v["policies"][0]["rules"][0]["idents"].as_array().unwrap();
        assert_eq!(idents[0], "a.b.c");
        assert_eq!(idents[1], "d");
    }

    #[test]
    fn parses_boundary_with_phases() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node gw : authenticated
            node audit_log : trusted { attr append_only; }
            node view : trusted
            flow f1 : gw -> gw
            boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified" {
                admit { rate_limit 20 req/min; max_size 64 KiB; }
                parse { time linear; frame {} }
                judge {}
                effect { frame { gw } }
                record { audit to audit_log }
                refuse { respond Public; frame { audit_log } }
            }"#);
        let phases = &v["boundaries"][0]["phases"];
        assert_eq!(phases["admit"]["max_size"]["value"], 64.0);
        assert_eq!(phases["parse"]["time"], "linear");
        assert_eq!(phases["judge"], true);
        assert_eq!(phases["effect"]["frame"][0], "gw");
        assert_eq!(phases["record"]["audit_to"], "audit_log");
        assert_eq!(phases["refuse"]["respond"], "Public");
        assert_eq!(phases["refuse"]["frame"][0], "audit_log");
    }

    #[test]
    fn parses_boundary_without_phases_is_still_legal() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            boundary b1 endorse f1 : foreign -> authenticated"#);
        assert!(v["boundaries"][0]["phases"].is_null());
    }

    #[test]
    fn parses_operation_with_ok_and_err_frames() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            operation Transfer on LedgerDb {
                modifies { Balance(from), Balance(to) } on Ok;
                modifies {} on Err;
                atomic via LedgerDb
            }"#);
        let op = &v["operations"][0];
        assert_eq!(op["id"], "Transfer");
        assert_eq!(op["on"], "LedgerDb");
        assert_eq!(op["modifies_ok"][0], "Balance(from)");
        assert_eq!(op["modifies_ok"][1], "Balance(to)");
        assert_eq!(op["modifies_err"].as_array().unwrap().len(), 0);
        assert_eq!(op["atomic_via"], "LedgerDb");
    }

    #[test]
    fn parses_node_with_errors_total_panics_and_observe() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node api : trusted {
                errors_total;
                panics_contained_by supervisor;
                observe { log error_paths, boundary_crossings; to obs_sink }
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["errors_total"], true);
        assert_eq!(n["panics_contained_by"], "supervisor");
        assert_eq!(n["observe"]["log"][0], "error_paths");
        assert_eq!(n["observe"]["log"][1], "boundary_crossings");
        assert_eq!(n["observe"]["to"], "obs_sink");
    }

    #[test]
    fn parses_bare_node_defaults_observability_fields() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\n            node api : trusted");
        let n = &v["nodes"][0];
        assert_eq!(n["errors_total"], false);
        assert!(n["panics_contained_by"].is_null());
        assert!(n["observe"].is_null());
    }

    #[test]
    fn duplicate_phase_keyword_is_a_parse_error() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            boundary b1 endorse f1 : foreign -> authenticated {
                judge {}
                judge {}
            }"#);
        assert!(e["message"].as_str().unwrap().contains("duplicate judge"));
    }

    #[test]
    fn fuzz_safe_random_bytes_never_panic() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let samples = [
            "\0\0\0",
            "module",
            "{{{{",
            "module m node",
            "assert c bound age x <= ",
            "\"unterminated",
            "module m\n// comment only\n",
        ];
        for s in samples {
            let out = parse_source_impl(s);
            assert!(serde_json::from_str::<Value>(&out).is_ok());
        }
    }

    #[test]
    fn parses_scenario_with_all_rewrite_kinds_and_nested_claims() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            scenario node_loss {
                remove n1;
                scale f1 by 3.0;
                trust n2 := foreign;
                assert c1 noflow n1 -> n2;
                assume c2 bound rate f1 <= 10 req/s owner alice review "2026-01-01";
            }"#);
        let s = &v["scenarios"][0];
        assert_eq!(s["id"], "node_loss");
        assert_eq!(s["rewrites"][0]["kind"], "remove");
        assert_eq!(s["rewrites"][0]["node_id"], "n1");
        assert_eq!(s["rewrites"][1]["kind"], "scale");
        assert_eq!(s["rewrites"][1]["flow_id"], "f1");
        assert_eq!(s["rewrites"][1]["factor"], 3.0);
        assert_eq!(s["rewrites"][2]["kind"], "trust");
        assert_eq!(s["rewrites"][2]["node_id"], "n2");
        assert_eq!(s["rewrites"][2]["level"], "foreign");
        assert_eq!(s["claims"][0]["id"], "c1");
        assert_eq!(s["claims"][0]["kind"], "noflow");
        assert_eq!(s["claims"][1]["id"], "c2");
        assert_eq!(s["claims"][1]["assumed"], true);
        // scenario-local claims never leak into the module's top-level list
        assert_eq!(v["claims"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parses_bare_scenario_with_no_rewrites_or_claims() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nscenario s { }");
        let s = &v["scenarios"][0];
        assert_eq!(s["id"], "s");
        assert_eq!(s["rewrites"].as_array().unwrap().len(), 0);
        assert_eq!(s["claims"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn error_scenario_rejects_unknown_statement() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nscenario s { bogus x; }");
        assert_eq!(
            e["message"],
            "expected remove, scale, trust, assert, or assume inside scenario block"
        );
    }

    #[test]
    fn error_scenario_trust_requires_coloneq() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err("module m\nscenario s { trust n1 = foreign; }");
        assert_eq!(e["message"], "expected :=");
    }

    // T-0700: `access "RESOURCE" mode MODE` node/store clause + `resource
    // ID { arbitrated_by NODE | lock "NAME" }` top-level construct.

    #[test]
    fn parses_node_access_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node writer : trusted {
                access "ledger_db" mode write;
                access "cache_db" mode read;
            }"#);
        let n = &v["nodes"][0];
        let attrs: Vec<&str> = n["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"access=ledger_db:write"));
        assert!(attrs.contains(&"access=cache_db:read"));
    }

    #[test]
    fn parses_store_access_clause() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261 node/store symmetry: same `access` shape on `store`.
        let v = ok(r#"module m
            store ledger_db : trusted {
                access "ledger_db" mode exclusive;
            }"#);
        let s = &v["stores"][0];
        let attrs: Vec<&str> = s["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        assert!(attrs.contains(&"access=ledger_db:exclusive"));
    }

    #[test]
    fn parses_all_access_modes() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node n : trusted {
                access "r" mode read;
                access "a" mode append;
                access "al" mode alpha;
                access "w" mode write;
                access "e" mode exclusive;
            }"#);
        let attrs: Vec<&str> = v["nodes"][0]["attrs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|a| a.as_str().unwrap())
            .collect();
        for expect in [
            "access=r:read",
            "access=a:append",
            "access=al:alpha",
            "access=w:write",
            "access=e:exclusive",
        ] {
            assert!(attrs.contains(&expect), "missing {expect:?} in {attrs:?}");
        }
    }

    #[test]
    fn error_access_rejects_unknown_mode() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node n : trusted {
                access "r" mode bogus;
            }"#);
        assert_eq!(
            e["message"],
            "access mode must be one of read|append|alpha|write|exclusive"
        );
    }

    #[test]
    fn error_access_requires_mode_keyword() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            node n : trusted {
                access "r" write;
            }"#);
        assert_eq!(e["message"], "expected keyword \"mode\"");
    }

    #[test]
    fn parses_resource_with_arbitrated_by() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node writer : trusted { }
            resource ledger_db {
                arbitrated_by writer;
            }"#);
        let r = &v["resources"][0];
        assert_eq!(r["id"], "ledger_db");
        assert_eq!(r["arbitrated_by"], "writer");
        assert_eq!(r["lock"], serde_json::Value::Null);
    }

    #[test]
    fn parses_resource_with_lock() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            resource ledger_db {
                lock "ledger-lease";
            }"#);
        let r = &v["resources"][0];
        assert_eq!(r["id"], "ledger_db");
        assert_eq!(r["arbitrated_by"], serde_json::Value::Null);
        assert_eq!(r["lock"], "ledger-lease");
    }

    #[test]
    fn parses_bare_resource_with_no_arbiter() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nresource ledger_db");
        let r = &v["resources"][0];
        assert_eq!(r["id"], "ledger_db");
        assert_eq!(r["arbitrated_by"], serde_json::Value::Null);
        assert_eq!(r["lock"], serde_json::Value::Null);
    }

    #[test]
    fn error_resource_rejects_both_arbitrated_by_and_lock() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let e = err(r#"module m
            resource ledger_db {
                arbitrated_by writer;
                lock "ledger-lease";
            }"#);
        assert_eq!(
            e["message"],
            "resource may declare at most one of arbitrated_by/lock"
        );
    }

    // T-0702: `users NUMBER` / `rate NUMBER UNIT` entry-demand clauses.

    #[test]
    fn parses_node_users_and_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok(r#"module m
            node entry_a : trusted {
                users 300000;
                rate 500 req/s;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["users"], 300000.0);
        assert_eq!(n["rate"]["value"], 500.0);
        assert_eq!(n["rate"]["unit"], "req/s");
    }

    #[test]
    fn parses_node_without_users_or_rate_defaults_null() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nnode plain : trusted { }");
        let n = &v["nodes"][0];
        assert_eq!(n["users"], serde_json::Value::Null);
        assert_eq!(n["rate"], serde_json::Value::Null);
    }

    #[test]
    fn parses_node_users_only_no_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        let v = ok("module m\nnode entry_a : trusted { users 200000; }");
        let n = &v["nodes"][0];
        assert_eq!(n["users"], 200000.0);
        assert_eq!(n["rate"], serde_json::Value::Null);
    }

    #[test]
    fn parses_store_users_and_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // T-0261 node/store symmetry: same `users`/`rate` shape on `store`.
        let v = ok(r#"module m
            store db : trusted {
                users 500000;
                rate 1000 req/s;
            }"#);
        let s = &v["stores"][0];
        assert_eq!(s["users"], 500000.0);
        assert_eq!(s["rate"]["value"], 1000.0);
        assert_eq!(s["rate"]["unit"], "req/s");
    }

    #[test]
    fn parses_node_rate_does_not_collide_with_capacity_rate() {
        // frob:tests strata-core/src/lib.rs::parse_source kind="unit"
        // The top-level `rate` (T-0702 demand) and `capacity`'s own
        // nested rate quantity are independent fields.
        let v = ok(r#"module m
            node svc : trusted {
                rate 300 req/s;
                capacity 100 req/s replicas 1..3;
            }"#);
        let n = &v["nodes"][0];
        assert_eq!(n["rate"]["value"], 300.0);
        assert_eq!(n["capacity"]["rate"]["value"], 100.0);
    }
}
