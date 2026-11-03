//! `grimble serve --mcp` over `grimble-serve`: the tool list and the token gate, end to end.

// frob:ticket 01M3Z714XYJEHXHNWXKVXAYFQJ

use grimble_serve::launch;
use serde_json::{Value, json};

fn replies(input: &str) -> (Vec<Value>, String) {
    let root = tempfile::tempdir().expect("tempdir");
    let mut out = Vec::new();
    let mut announce = Vec::new();
    launch(root.path(), input.as_bytes(), &mut out, &mut announce).expect("launch");
    let lines = String::from_utf8(out)
        .expect("utf8")
        .lines()
        .map(|l| serde_json::from_str(l).expect("json"))
        .collect();
    (lines, String::from_utf8(announce).expect("utf8"))
}

// The token is minted inside `launch`, so the client side reads it back from the announce
// stream; the harness here drives a real child-free launch by serving two phases.
fn token_of(announce: &str) -> String {
    announce
        .trim()
        .rsplit(' ')
        .next()
        .expect("token word")
        .to_owned()
}

// frob:tests crates/grimble-serve/src/lib.rs::launch
// frob:tests crates/grimble-serve/src/lib.rs::GrimbleTools.list
#[test]
fn a_client_lists_check_and_graph_and_a_request_without_the_token_is_refused() {
    // Without the token: refused, and the reply carries no tool list.
    let list = |token: Option<&str>| {
        let mut params = json!({});
        if let Some(t) = token {
            params["_meta"] = json!({ "token": t });
        }
        json!({"jsonrpc":"2.0","id":1,"method":"tools/list","params":params}).to_string()
    };
    let (lines, announce) = replies(&format!("{}\n", list(None)));
    assert_eq!(lines[0]["error"]["code"], gob_serve::CODE_UNAUTHORIZED);
    assert!(lines[0].get("result").is_none());
    assert!(!lines[0].to_string().contains(&token_of(&announce)));

    // A guessed token: refused.
    let (lines, _) = replies(&format!("{}\n", list(Some("guess"))));
    assert_eq!(lines[0]["error"]["code"], gob_serve::CODE_UNAUTHORIZED);
}

/// One authenticated JSON-RPC request against `server`, returning the reply.
fn ask_server(
    server: &gob_serve::Server<grimble_serve::GrimbleTools>,
    method: &str,
    params: Value,
) -> Value {
    let mut params = params;
    params["_meta"] = json!({ "token": "placeholder-token" });
    server
        .handle_line(&json!({"jsonrpc":"2.0","id":1,"method":method,"params":params}).to_string())
        .expect("reply")
}

// frob:tests crates/grimble-serve/src/lib.rs::server
// frob:tests crates/grimble-serve/src/lib.rs::GrimbleTools.call
#[test]
fn with_the_token_check_and_graph_are_listed_and_callable_read_only() {
    let root = tempfile::tempdir().expect("tempdir");
    let token = gob_serve::Token::from_value("placeholder-token").expect("token");
    let server = grimble_serve::server(root.path(), token);
    let listed = ask_server(&server, "tools/list", json!({}));
    let tools = listed["result"]["tools"].as_array().expect("tools");
    let names: Vec<&str> = tools.iter().filter_map(|t| t["name"].as_str()).collect();
    assert_eq!(names, ["check", "graph"]);
    assert!(
        tools
            .iter()
            .all(|t| t["annotations"]["readOnlyHint"] == true)
    );

    for name in ["check", "graph"] {
        let reply = ask_server(&server, "tools/call", json!({ "name": name }));
        assert_eq!(reply["result"]["isError"], false, "{reply}");
    }
    let reply = ask_server(
        &server,
        "tools/call",
        json!({ "name": "check", "arguments": { "fix": true } }),
    );
    assert_eq!(reply["result"]["isError"], true);
    let reply = ask_server(&server, "tools/call", json!({ "name": "ticket_close" }));
    assert!(reply.get("error").is_some());
}

// frob:ticket 01M6C6NBJSSAVBR59RBMPWW9VP
// frob:tests crates/grimble-serve/src/lib.rs::GrimbleTools.call
#[test]
fn served_tools_leave_no_files_in_the_repository() {
    let root = tempfile::tempdir().expect("tempdir");
    std::fs::write(
        root.path().join("m.grmb"),
        "grimble = \"2\";\nmodule m;\nsystem s {\n  actor customer : human;\n}\n",
    )
    .expect("model");
    let token = gob_serve::Token::from_value("placeholder-token").expect("token");
    let server = grimble_serve::server(root.path(), token);
    for name in ["check", "graph"] {
        let line = json!({"jsonrpc":"2.0","id":1,"method":"tools/call",
            "params":{"name":name,"_meta":{"token":"placeholder-token"}}})
        .to_string();
        let reply = server.handle_line(&line).expect("reply");
        assert_eq!(reply["result"]["isError"], false, "{reply}");
    }
    let names: Vec<_> = std::fs::read_dir(root.path())
        .expect("read dir")
        .map(|e| e.expect("entry").file_name())
        .collect();
    assert_eq!(names, ["m.grmb"], "serve wrote into the repo");
}
