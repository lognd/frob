//! `frob serve` lists the ticket, lease and evidence read verbs as MCP tools and answers them with the CLI envelope.
// frob:ticket 01M4H2C3YV4ZDRNNTVKKYD6J5K

use std::fmt::Write as _;
use std::io::Cursor;
use std::path::Path;

use serde_json::{Value, json};

use crate::common;

/// Tools the acceptance names; deprecated aliases are not listed, their replacements are.
const READ_TOOLS: [&str; 6] = [
    "frob_ticket_show",
    "frob_ticket_list",
    "frob_ticket_doable",
    "frob_ticket_doctor",
    "frob_lease_list",
    "frob_ticket_evidence_list",
];

/// Mutating verbs that must never be offered.
const WRITE_TOOLS: [&str; 5] = [
    "frob_ticket_new",
    "frob_ticket_start",
    "frob_ticket_close",
    "frob_lease_widen",
    "frob_ticket_evidence_add",
];

/// A repository with `frob init` run and one commit.
fn repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    let out = common::frob_command()
        .current_dir(dir.path())
        .args(["--json", "init"])
        .output()
        .expect("run frob init");
    assert_eq!(out.status.code(), Some(0), "init");
    dir
}

/// Send `requests` to the MCP server rooted at `dir` and return the replies in order.
fn mcp(dir: &Path, requests: &[Value]) -> Vec<Value> {
    let mut input = String::new();
    for r in requests {
        writeln!(input, "{r}").expect("write to string");
    }
    let mut out = Vec::new();
    frob_cli::cli()
        .serve_mcp(Cursor::new(input), &mut out, dir)
        .expect("serve");
    String::from_utf8(out)
        .expect("utf8")
        .lines()
        .map(|l| serde_json::from_str(l).expect("json reply"))
        .collect()
}

/// The CLI's JSON envelope for `args` in `dir`.
fn cli_envelope(root: &Path, args: &[&str]) -> Value {
    let mut words = vec!["--json"];
    words.extend_from_slice(args);
    let out = common::frob_command()
        .current_dir(root)
        .args(words)
        .output()
        .expect("run frob");
    serde_json::from_slice(&out.stdout).expect("envelope")
}

/// The envelope text of the one `tools/call` reply.
fn call(dir: &Path, name: &str, arguments: &Value) -> (Value, bool) {
    let req = json!({"jsonrpc":"2.0","id":1,"method":"tools/call",
        "params":{"name":name,"arguments":arguments}});
    let reply = mcp(dir, &[req]).remove(0);
    let result = &reply["result"];
    let text = result["content"][0]["text"].as_str().expect("text");
    (
        serde_json::from_str(text).expect("envelope json"),
        result["isError"].as_bool().expect("isError"),
    )
}

// frob:tests crates/frob/src/ticket/read.rs::Show
// frob:tests crates/frob/src/ticket/read.rs::List
// frob:tests crates/frob/src/ticket/read.rs::Doable
// frob:tests crates/frob/src/ticket/doctor_cmd.rs::TicketDoctor
// frob:tests crates/frob-lease/src/verbs.rs::LeaseList
// frob:tests crates/frob-evidence/src/verbs.rs::ListVerb
#[test]
fn tools_list_offers_the_read_verbs_with_schemas_and_no_mutating_verb() {
    let dir = repo();
    let req = json!({"jsonrpc":"2.0","id":1,"method":"tools/list"});
    let reply = mcp(dir.path(), &[req]).remove(0);
    let tools = reply["result"]["tools"].as_array().expect("tools");
    let names: Vec<&str> = tools.iter().filter_map(|t| t["name"].as_str()).collect();
    for want in READ_TOOLS {
        let tool = tools
            .iter()
            .find(|t| t["name"] == want)
            .unwrap_or_else(|| panic!("{want} not listed in {names:?}"));
        assert_eq!(tool["inputSchema"]["type"], "object", "{want} schema");
        assert_eq!(tool["annotations"]["readOnlyHint"], true, "{want} hint");
    }
    for bad in WRITE_TOOLS {
        assert!(!names.contains(&bad), "{bad} must not be exposed");
    }
    let doctor = tools
        .iter()
        .find(|t| t["name"] == "frob_ticket_doctor")
        .expect("doctor");
    assert!(
        doctor["inputSchema"]["properties"].get("fix").is_none(),
        "the write flag --fix must stay hidden"
    );
}

// frob:tests crates/frob/src/ticket/read.rs::Doable
// frob:tests crates/frob/src/ticket/read.rs::Show
// frob:tests crates/frob-lease/src/verbs.rs::LeaseList
#[test]
fn read_tool_calls_return_the_same_envelope_as_the_cli() {
    let dir = repo();
    let made = cli_envelope(
        dir.path(),
        &["ticket", "new", "--title", "t", "--type", "task"],
    );
    let id = made["data"]["id"].as_str().expect("id").to_owned();
    let (doable, is_error) = call(dir.path(), "frob_ticket_doable", &json!({}));
    assert!(!is_error);
    assert_eq!(doable, cli_envelope(dir.path(), &["ticket", "doable"]));
    let (show, _) = call(dir.path(), "frob_ticket_show", &json!({"ticket": id}));
    assert_eq!(show, cli_envelope(dir.path(), &["ticket", "show", &id]));
    let (leases, _) = call(dir.path(), "frob_lease_list", &json!({}));
    assert_eq!(leases, cli_envelope(dir.path(), &["lease", "list"]));
}

// frob:tests crates/frob/src/ticket/read.rs::Show
#[test]
fn a_failing_read_call_is_an_envelope_not_a_transport_error() {
    let dir = repo();
    let (env, _) = call(
        dir.path(),
        "frob_ticket_show",
        &json!({"ticket": "~NOSUCH0"}),
    );
    assert_ne!(env["ok"], json!(true), "{env}");
    let req = json!({"jsonrpc":"2.0","id":2,"method":"tools/call",
        "params":{"name":"frob_ticket_new","arguments":{}}});
    let reply = mcp(dir.path(), &[req]).remove(0);
    assert_eq!(reply["error"]["code"], -32602, "mutating verb is unknown");
}
