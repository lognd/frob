//! TESTQ001 to TESTQ003: test without assertion, nondeterminism in a test, control flow in a test.

// frob:ticket 01M4D957J2HZ655A1H8DJ4K8YD
// frob:ticket 01M5HJNEBY5YBCJB06D5ZSH4H5
// frob:ticket 01M5K9QNQFYJNXZSSG2X91FJBQ

use std::path::Path;

use gob_languages::Language;
use grimble_lints::res::Certainty;
use grimble_lints::testq::{Kind, Report, has_test_roles, is_test_file, scan};

fn report(lang: Language, src: &str) -> Report {
    scan(lang, src).expect("fixture parses")
}

fn of(lang: Language, src: &str, kind: Kind) -> Vec<(String, Certainty)> {
    report(lang, src)
        .sites
        .into_iter()
        .filter(|s| s.kind == kind)
        .map(|s| (s.detail, s.certainty))
        .collect()
}

fn rust(src: &str, kind: Kind) -> Vec<(String, Certainty)> {
    of(Language::Rust, src, kind)
}

fn py(src: &str, kind: Kind) -> Vec<(String, Certainty)> {
    of(Language::Python, src, kind)
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn rust_test_without_assertion_fires() {
    let src = "#[test]\nfn smoke() {\n    let x = compute();\n    drop(x);\n}\n";
    assert_eq!(
        rust(src, Kind::NoAssertion),
        [("smoke".to_owned(), Certainty::Certain)]
    );
    let asserting = "#[test]\nfn ok() {\n    assert_eq!(compute(), 1);\n}\n";
    assert!(rust(asserting, Kind::NoAssertion).is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn python_test_without_assertion_fires() {
    let src = "def test_smoke():\n    x = compute()\n    print(x)\n";
    assert_eq!(
        py(src, Kind::NoAssertion),
        [("test_smoke".to_owned(), Certainty::Certain)]
    );
    let asserting = "def test_ok():\n    assert compute() == 1\n";
    assert!(py(asserting, Kind::NoAssertion).is_empty());
    let raising = "def test_r():\n    with pytest.raises(ValueError):\n        compute()\n";
    assert!(py(raising, Kind::NoAssertion).is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn same_file_helper_that_asserts_makes_the_test_clean() {
    let src = "fn check(v: i32) { assert_eq!(v, 1); }\n\
               fn outer(v: i32) { check(v); }\n\
               #[test]\nfn t() { outer(compute()); }\n";
    assert!(rust(src, Kind::NoAssertion).is_empty());
    let silent = "fn finish(v: i32) { drop(v); }\n#[test]\nfn t() { finish(compute()); }\n";
    assert_eq!(rust(silent, Kind::NoAssertion).len(), 1);
    let methods = "class TestA:\n    def helper(self):\n        assert 1\n    def test_a(self):\n        self.helper()\n";
    assert!(py(methods, Kind::NoAssertion).is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn helper_with_unseen_body_is_unresolved_not_a_hit() {
    let imported = "use crate::support::verify_ok;\n#[test]\nfn t() { run(); verify_ok(); }\n";
    // The name alone reads as a check, so this one is clean.
    assert!(rust(imported, Kind::NoAssertion).is_empty());
    let opaque = "use crate::support::finish;\n#[test]\nfn t() { run(); finish(); }\n";
    assert_eq!(
        rust(opaque, Kind::NoAssertion),
        [("t".to_owned(), Certainty::Unknown)]
    );
    let module = "mod harness;\n#[test]\nfn t() { harness::drive(); }\n";
    assert_eq!(
        rust(module, Kind::NoAssertion),
        [("t".to_owned(), Certainty::Unknown)]
    );
    let relative = "from .base import finish\ndef test_t():\n    finish()\n";
    assert_eq!(
        py(relative, Kind::NoAssertion),
        [("test_t".to_owned(), Certainty::Unknown)]
    );
    let mixin = "class TestA(Mixin):\n    def test_a(self):\n        self.run_all()\n";
    assert_eq!(
        py(mixin, Kind::NoAssertion),
        [("test_a".to_owned(), Certainty::Unknown)]
    );
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn exempt_tests_are_not_flagged() {
    let panics = "#[test]\n#[should_panic]\nfn t() { boom(); }\n";
    assert!(rust(panics, Kind::NoAssertion).is_empty());
    let result = "#[test]\nfn t() -> Result<(), E> { run()?; Ok(()) }\n";
    assert!(rust(result, Kind::NoAssertion).is_empty());
    let ignored = "#[test]\n#[ignore]\nfn t() { std::thread::sleep(D); }\n";
    assert!(report(Language::Rust, ignored).sites.is_empty());
    let not_a_test = "fn t() { run(); }\n#[cfg(test)]\nmod m { fn h() { run(); } }\n";
    assert!(report(Language::Rust, not_a_test).sites.is_empty());
    let skipped = "@pytest.mark.skip(reason='x')\ndef test_t():\n    time.sleep(1)\n";
    assert!(report(Language::Python, skipped).sites.is_empty());
    let skipping = "def test_t():\n    pytest.skip('later')\n";
    assert!(py(skipping, Kind::NoAssertion).is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn async_and_attribute_variants_are_tests() {
    let src = "#[tokio::test]\nasync fn t() { run().await; }\n";
    assert_eq!(rust(src, Kind::NoAssertion).len(), 1);
    let q = "class TestA(unittest.TestCase):\n    async def test_a(self):\n        await run()\n";
    assert_eq!(py(q, Kind::NoAssertion).len(), 1);
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn sleep_in_a_test_body_fires() {
    let src = "#[test]\nfn t() {\n    std::thread::sleep(D);\n    assert!(done());\n}\n";
    let hits = rust(src, Kind::Nondeterminism);
    assert_eq!(hits.len(), 1);
    assert!(hits[0].0.ends_with("thread::sleep"));
    let imported = "use std::thread::sleep;\n#[test]\nfn t() { sleep(D); assert!(done()); }\n";
    assert_eq!(rust(imported, Kind::Nondeterminism).len(), 1);
    let aliased = "use std::thread;\n#[test]\nfn t() { thread::sleep(D); assert!(done()); }\n";
    assert_eq!(rust(aliased, Kind::Nondeterminism).len(), 1);
    let p = "import time\ndef test_t():\n    time.sleep(1)\n    assert done()\n";
    assert_eq!(py(p, Kind::Nondeterminism).len(), 1);
    let from = "from time import sleep as nap\ndef test_t():\n    nap(1)\n    assert done()\n";
    assert_eq!(py(from, Kind::Nondeterminism).len(), 1);
    let asy = "import asyncio\nasync def test_t():\n    await asyncio.sleep(2)\n    assert 1\n";
    assert_eq!(py(asy, Kind::Nondeterminism).len(), 1);
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn pinned_sources_are_exempt() {
    let paused = "#[tokio::test(start_paused = true)]\nasync fn t() { tokio::time::sleep(D).await; assert!(1); }\n";
    assert!(rust(paused, Kind::Nondeterminism).is_empty());
    let zero = "import time\ndef test_t():\n    time.sleep(0)\n    assert 1\n";
    assert!(py(zero, Kind::Nondeterminism).is_empty());
    let frozen = "@freeze_time('2020-01-01')\ndef test_t():\n    datetime.now()\n    assert 1\n";
    assert!(py(frozen, Kind::Nondeterminism).is_empty());
    let seeded =
        "import random\ndef test_t():\n    random.seed(1)\n    random.random()\n    assert 1\n";
    assert!(py(seeded, Kind::Nondeterminism).is_empty());
    let modseed =
        "import random\nrandom.seed(1)\ndef test_t():\n    random.random()\n    assert 1\n";
    assert!(py(modseed, Kind::Nondeterminism).is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn wall_clock_and_unseeded_rng_fire() {
    let rs = "use std::time::Instant;\n#[test]\nfn t() { let s = Instant::now(); let r = rand::thread_rng(); assert!(1); }\n";
    assert_eq!(rust(rs, Kind::Nondeterminism).len(), 2);
    let pt = "import time, random\nfrom datetime import datetime\ndef test_t():\n    time.time()\n    datetime.now()\n    random.random()\n    random.Random()\n    assert 1\n";
    assert_eq!(py(pt, Kind::Nondeterminism).len(), 4);
    let seeded_ctor = "import random\ndef test_t():\n    random.Random(7)\n    assert 1\n";
    assert!(py(seeded_ctor, Kind::Nondeterminism).is_empty());
    let outside = "fn prod() { std::thread::sleep(D); }\n#[test]\nfn t() { assert!(1); }\n";
    assert!(rust(outside, Kind::Nondeterminism).is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
// frob:tests crates/grimble-lints/src/testq.rs::Kind.default_enabled
#[test]
fn control_flow_reports_the_outermost_construct_and_is_off_by_default() {
    let src = "#[test]\nfn t() {\n    for i in 0..3 {\n        if i > 1 { assert!(i); }\n    }\n    match x { _ => {} }\n}\n";
    let flow = rust(src, Kind::ControlFlow);
    assert_eq!(
        flow.iter().map(|(d, _)| d.as_str()).collect::<Vec<_>>(),
        ["for_expression", "match_expression"]
    );
    let p = "def test_t():\n    if a:\n        assert 1\n    while b:\n        pass\n    def inner():\n        if c: pass\n";
    assert_eq!(py(p, Kind::ControlFlow).len(), 2);
    assert!(!Kind::ControlFlow.default_enabled());
    assert!(Kind::NoAssertion.default_enabled());
    assert!(Kind::Nondeterminism.default_enabled());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
// frob:tests crates/grimble-lints/src/testq.rs::has_test_roles
#[test]
fn language_without_roles_is_unresolved_not_clean() {
    assert!(has_test_roles(Language::Rust));
    assert!(!has_test_roles(Language::Yaml));
    let r = report(Language::Yaml, "a: 1\n");
    assert!(r.sites.is_empty());
    assert_eq!(
        r.unresolved,
        [Kind::NoAssertion, Kind::Nondeterminism, Kind::ControlFlow]
    );
}

// frob:tests crates/grimble-lints/src/testq.rs::Kind.rule_id
#[test]
fn rule_ids_follow_kinds() {
    assert_eq!(Kind::NoAssertion.rule_id(), "TESTQ001");
    assert_eq!(Kind::Nondeterminism.rule_id(), "TESTQ002");
    assert_eq!(Kind::ControlFlow.rule_id(), "TESTQ003");
}

// frob:tests crates/grimble-lints/src/testq.rs::is_test_file
#[test]
fn python_test_files_are_recognised_by_name_and_directory() {
    assert!(is_test_file(Path::new("pkg").join("test_a.py").as_path()));
    assert!(is_test_file(Path::new("a_test.py")));
    assert!(is_test_file(Path::new("conftest.py")));
    assert!(is_test_file(Path::new("tests").join("x.py").as_path()));
    assert!(!is_test_file(Path::new("pkg").join("main.py").as_path()));
}

// frob:tests crates/grimble-lints/src/testq.rs::is_test_file
#[test]
fn script_and_csharp_test_files_are_recognised_by_name() {
    assert!(is_test_file(Path::new("add.test.ts")));
    assert!(is_test_file(Path::new("add.spec.js")));
    assert!(is_test_file(
        Path::new("__tests__").join("add.ts").as_path()
    ));
    assert!(is_test_file(Path::new("AddTests.cs")));
    assert!(is_test_file(Path::new("AddTest.cs")));
    assert!(!is_test_file(Path::new("add.ts")));
    assert!(!is_test_file(Path::new("Latest.py")));
}

fn ts(src: &str) -> Vec<(String, Certainty)> {
    of(Language::TypeScript, src, Kind::NoAssertion)
}

fn cs(src: &str) -> Vec<(String, Certainty)> {
    of(Language::CSharp, src, Kind::NoAssertion)
}

/// A relative module specifier, built without a literal separator.
fn rel(name: &str) -> String {
    format!(".{}{name}", std::path::MAIN_SEPARATOR)
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn ts_and_js_assertion_calls_are_classified_not_unresolved() {
    let asserting = [
        "test('a', () => { expect(add(1, 2)).toBe(3); });",
        "it('a', () => { expect(x).not.toBe(1); });",
        "it('a', async () => { await expect(p).rejects.toThrow(); });",
        "it('a', function () { expect(x).toMatchSnapshot(); });",
        "import assert from 'node:assert/strict';\nit('a', () => { assert.equal(1, 1); });",
        "const assert = require('assert');\nit('a', () => { assert.deepStrictEqual(a, b); });",
        "import { strictEqual } from 'assert';\nit('a', () => { strictEqual(1, 1); });",
        "it('a', () => { x.should.equal(1); });",
        "it('a', () => { chai.expect(x).to.equal(1); });",
        "test('a', (t) => { t.is(1, 1); });",
        "it('a', () => { expectTypeOf(x).toEqualTypeOf<number>(); });",
    ];
    for src in asserting {
        assert!(ts(src).is_empty(), "should be clean: {src}");
        assert!(
            of(Language::JavaScript, src, Kind::NoAssertion).is_empty(),
            "js: {src}"
        );
    }
    assert!(
        ts("it('a', () => { expect(x).toBe(1); });").is_empty()
            && report(Language::Tsx, "it('a', () => { expect(x).toBe(1); });")
                .unresolved
                .iter()
                .all(|k| *k != Kind::NoAssertion)
    );
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn ts_test_without_assertion_fires_and_unknown_helpers_stay_unresolved() {
    assert_eq!(
        ts("it('does nothing', () => { const x = add(1, 2); log(x); });"),
        [("does nothing".to_owned(), Certainty::Certain)]
    );
    let helper = format!(
        "import {{ finish }} from '{}';\nit('a', () => {{ finish(); }});",
        rel("helpers")
    );
    assert_eq!(ts(&helper), [("a".to_owned(), Certainty::Unknown)]);
    let unit = format!(
        "import {{ add }} from '{}';\nit('a', () => {{ add(1, 2); }});",
        rel("add")
    );
    assert_eq!(ts(&unit), [("a".to_owned(), Certainty::Certain)]);
    let local = "function check2(x) { expect(x).toBe(1); }\nit('a', () => { check2(1); });";
    assert!(ts(local).is_empty());
    let local_none = "function run(x) { return x; }\nit('a', () => { run(1); });";
    assert_eq!(ts(local_none).len(), 1);
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn ts_skipped_grouped_and_callbackless_tests_are_handled() {
    assert!(ts("it.skip('a', () => {});").is_empty());
    assert!(ts("xit('a', () => {});").is_empty());
    assert!(ts("it.todo('a');").is_empty());
    assert!(ts("describe.skip('s', () => { it('a', () => {}); });").is_empty());
    assert!(ts("describe('s', () => { beforeEach(() => { setup(); }); });").is_empty());
    assert_eq!(
        ts("describe('s', () => { it.only('a', () => { run(); }); });").len(),
        1
    );
    assert_eq!(ts("it.each([1, 2])('n %d', (n) => { run(n); });").len(), 1);
    assert!(ts("it.each([1, 2])('n %d', (n) => { expect(n).toBe(n); });").is_empty());
    let r = report(
        Language::TypeScript,
        "it('a', () => { expect(1).toBe(1); });",
    );
    assert!(r.unresolved.is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn csharp_assertion_calls_are_classified_not_unresolved() {
    let wrap = |body: &str| {
        format!(
            "using Xunit;\nnamespace T {{\n public class AddTests {{\n  [Fact]\n  public void A() {{ {body} }}\n }}\n}}\n"
        )
    };
    for body in [
        "Assert.Equal(3, Add(1, 2));",
        "Assert.Throws<ArgumentException>(() => Add(-1, 0));",
        "await Assert.ThrowsAsync<InvalidOperationException>(() => Run());",
        "Assert.That(x, Is.EqualTo(1));",
        "x.Should().Be(1);",
        "await act.Should().ThrowAsync<InvalidOperationException>();",
        "mock.Received().Run();",
        "Assert.Multiple(() => { Assert.True(a); });",
    ] {
        assert!(cs(&wrap(body)).is_empty(), "should be clean: {body}");
    }
    let statics = "using static Xunit.Assert;\npublic class T {\n [Fact]\n public void A() { Equal(1, 1); }\n}\n";
    assert!(cs(statics).is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn csharp_test_without_assertion_fires_and_variants_are_handled() {
    let none = "public class T {\n [Fact]\n public void Smoke() { var x = Add(1, 2); }\n}\n";
    assert_eq!(cs(none), [("Smoke".to_owned(), Certainty::Certain)]);
    let nunit = "public class T {\n [Test]\n public void Smoke() { Add(1, 2); }\n}\n";
    assert_eq!(cs(nunit).len(), 1);
    let skipped = "public class T {\n [Fact(Skip = \"later\")]\n public void A() { Add(1, 2); }\n [Test, Ignore(\"x\")]\n public void B() { Add(1, 2); }\n}\n";
    assert!(cs(skipped).is_empty());
    let expected = "public class T {\n [TestCase(1, ExpectedResult = 2)]\n public int A(int x) { return x + 1; }\n}\n";
    assert!(cs(expected).is_empty());
    let not_a_test = "public class T {\n public void Helper() { Add(1, 2); }\n}\n";
    assert!(cs(not_a_test).is_empty());
    let open = "public class T : TestBase {\n [Fact]\n public void A() { Prepare(); }\n}\n";
    assert_eq!(cs(open), [("A".to_owned(), Certainty::Unknown)]);
    let closed = "public class T : IDisposable {\n [Fact]\n public void A() { Prepare(); }\n}\n";
    assert_eq!(cs(closed), [("A".to_owned(), Certainty::Certain)]);
    let local = "public class T {\n [Fact]\n public void A() { Verify2(); }\n void Verify2() { Assert.True(true); }\n}\n";
    assert!(cs(local).is_empty());
    let dbg = "public class T {\n [Fact]\n public void A() { Console.WriteLine(1); }\n}\n";
    assert_eq!(cs(dbg).len(), 1);
}

fn ts_kind(src: &str, kind: Kind) -> Vec<String> {
    of(Language::TypeScript, src, kind)
        .into_iter()
        .map(|(d, _)| d)
        .collect()
}

fn cs_kind(src: &str, kind: Kind) -> Vec<String> {
    let wrapped = format!("public class T {{\n [Fact]\n public void A() {{ {src} }}\n}}\n");
    of(Language::CSharp, &wrapped, kind)
        .into_iter()
        .map(|(d, _)| d)
        .collect()
}

fn it_body(body: &str) -> String {
    format!("it('a', async () => {{ {body} }});")
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn ts_js_and_csharp_nondeterminism_is_reported_not_unresolved() {
    let n = Kind::Nondeterminism;
    for (body, want) in [
        ("const x = Math.random();", "Math.random"),
        ("const t = Date.now();", "Date.now"),
        ("const d = new Date();", "new Date"),
        ("const t = performance.now();", "performance.now"),
        ("const u = crypto.randomUUID();", "crypto.randomUUID"),
        (
            "globalThis.crypto.getRandomValues(buf);",
            "globalThis.crypto.getRandomValues",
        ),
        (
            "await new Promise((r) => setTimeout(r, 100));",
            "setTimeout",
        ),
        ("window.setInterval(f, 5);", "window.setInterval"),
    ] {
        assert_eq!(ts_kind(&it_body(body), n), [want], "typescript: {body}");
        let js = of(Language::JavaScript, &it_body(body), n);
        assert_eq!(js.len(), 1, "javascript: {body}");
    }
    let imported = "import { randomBytes } from 'node:crypto';\nimport { setTimeout as wait } from 'node:timers/promises';\n";
    let src = format!("{imported}{}", it_body("randomBytes(4); await wait(10);"));
    assert_eq!(
        ts_kind(&src, n),
        ["crypto.randomBytes", "timers.promises.setTimeout"]
    );
    for (body, want) in [
        ("var t = DateTime.Now;", "DateTime.Now"),
        (
            "var t = System.DateTime.UtcNow.Ticks;",
            "System.DateTime.UtcNow",
        ),
        ("var t = DateTimeOffset.UtcNow;", "DateTimeOffset.UtcNow"),
        ("var g = Guid.NewGuid();", "Guid.NewGuid"),
        ("var r = new Random();", "new Random"),
        ("var v = Random.Shared.Next(5);", "Random.Shared.Next"),
        ("await Task.Delay(500);", "Task.Delay"),
        ("Thread.Sleep(10);", "Thread.Sleep"),
        ("var sw = Stopwatch.StartNew();", "Stopwatch.StartNew"),
    ] {
        assert_eq!(cs_kind(body, n), [want], "csharp: {body}");
    }
    let r = report(Language::TypeScript, &it_body("Math.random();"));
    assert!(r.unresolved.is_empty());
    let r = report(
        Language::CSharp,
        "public class T {\n [Fact]\n public void A() { Assert.True(true); }\n}\n",
    );
    assert!(r.unresolved.is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn ts_js_and_csharp_control_flow_is_reported_not_unresolved() {
    let c = Kind::ControlFlow;
    for (body, want) in [
        ("if (x) { run(); }", "if_statement"),
        ("for (let i = 0; i < 3; i++) { run(i); }", "for_statement"),
        ("for (const v of xs) { run(v); }", "for_in_statement"),
        ("while (go()) { run(); }", "while_statement"),
        ("do { run(); } while (go());", "do_statement"),
        ("switch (x) { case 1: run(); }", "switch_statement"),
        ("const v = ok ? 1 : 2;", "ternary_expression"),
        ("try { run(); } catch (e) { fail(e); }", "try_statement"),
    ] {
        assert_eq!(ts_kind(&it_body(body), c), [want], "typescript: {body}");
        assert_eq!(of(Language::JavaScript, &it_body(body), c).len(), 1);
    }
    // Only the outermost construct is reported; a callback is a separate function.
    assert_eq!(
        ts_kind(&it_body("if (a) { for (const v of xs) { run(v); } }"), c),
        ["if_statement"]
    );
    assert!(ts_kind(&it_body("xs.forEach((v) => { if (v) { run(); } });"), c).is_empty());
    for (body, want) in [
        ("if (x) { Run(); }", "if_statement"),
        ("for (var i = 0; i < 3; i++) { Run(i); }", "for_statement"),
        ("foreach (var v in xs) { Run(v); }", "foreach_statement"),
        ("while (Go()) { Run(); }", "while_statement"),
        ("do { Run(); } while (Go());", "do_statement"),
        ("switch (x) { case 1: Run(); break; }", "switch_statement"),
        ("var v = x switch { 1 => 2, _ => 3 };", "switch_expression"),
        ("var v = ok ? 1 : 2;", "conditional_expression"),
        ("try { Run(); } catch (Exception) { }", "try_statement"),
    ] {
        assert_eq!(cs_kind(body, c), [want], "csharp: {body}");
    }
    let r = report(Language::TypeScript, &it_body("if (x) { run(); }"));
    assert!(r.unresolved.is_empty());
}

// frob:tests crates/grimble-lints/src/testq.rs::scan
#[test]
fn deterministic_ts_js_and_csharp_tests_stay_quiet() {
    let n = Kind::Nondeterminism;
    let c = Kind::ControlFlow;
    for body in [
        "expect(add(1, 2)).toBe(3);",
        "const d = new Date(0); expect(d.getTime()).toBe(0);",
        "const d = new Date('2020-01-01T00:00:00Z'); expect(d).toBeDefined();",
        "const t = Date.parse('2020-01-01');",
        "expect(clock.now()).toBe(1); expect(rng.random()).toBe(2);",
        "expect(Math.randomize()).toBe(1); expect(MyDate.now()).toBe(1);",
        "expect(Math.floor(1.5)).toBe(1);",
        "setTimeout(done, 0);",
        "// Math.random() and Date.now() and if (x) are only words here\nexpect(1).toBe(1);",
        "const s = 'Math.random() Date.now() new Date() if (x) { } while (y)';\nexpect(s).toBeDefined();",
        "const s = `setTimeout ${1} for while`;\nexpect(s).toBeDefined();",
        "await fetch(url); expect(1).toBe(1);",
    ] {
        let src = it_body(body);
        assert!(ts_kind(&src, n).is_empty(), "nondet: {body}");
        assert!(ts_kind(&src, c).is_empty(), "flow: {body}");
    }
    for pinned in [
        "jest.useFakeTimers();\nit('a', () => { setTimeout(f, 10); Date.now(); new Date(); expect(1).toBe(1); });",
        "beforeEach(() => { vi.setSystemTime(0); });\nit('a', () => { Date.now(); expect(1).toBe(1); });",
        "vi.spyOn(Math, 'random').mockReturnValue(0.5);\nit('a', () => { Math.random(); expect(1).toBe(1); });",
        "Math.random = () => 4;\nit('a', () => { Math.random(); expect(1).toBe(1); });",
    ] {
        assert!(ts_kind(pinned, n).is_empty(), "pinned: {pinned}");
    }
    for body in [
        "var r = new Random(42); Assert.Equal(1, r.Next());",
        "var r = new System.Random(seed); Assert.True(r.Next() >= 0);",
        "Assert.Equal(1, clock.Now); Assert.Equal(2, MyDateTime.Now);",
        "Assert.Equal(3, Add(1, 2));",
        "Thread.Sleep(0); Assert.True(true);",
        "await Task.Delay(TimeSpan.FromSeconds(1), fakeTimeProvider); Assert.True(true);",
        "// DateTime.Now Guid.NewGuid() if (x) are only words here\nAssert.True(true);",
        "var s = \"DateTime.Now Guid.NewGuid() while (y) if (x)\"; Assert.NotNull(s);",
        "var d = new DateTime(2020, 1, 1); Assert.Equal(2020, d.Year);",
        "var c = await client.GetAsync(url); Assert.NotNull(c);",
    ] {
        assert!(cs_kind(body, n).is_empty(), "nondet: {body}");
        assert!(cs_kind(body, c).is_empty(), "flow: {body}");
    }
}
