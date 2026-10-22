//! UNITY201 and UNITY202: lookups and managed allocation in Unity hot code.

// frob:ticket CC940D3

use gob_languages::Language;
use grimble_lints::unity_common::Finding;
use grimble_lints::unity_hot::{RULE_ALLOC, RULE_LOOKUP, scan};

fn run(body: &str) -> Vec<Finding> {
    let src = format!("class P : MonoBehaviour {{ List<int> cache; Camera cam; {body} }}");
    scan(Language::CSharp, &src).expect("fixture parses")
}

fn rules(body: &str) -> Vec<&'static str> {
    run(body).iter().map(|f| f.rule).collect()
}

// frob:tests crates/grimble-lints/src/unity_hot.rs::scan
#[test]
fn get_component_reachable_from_update_fires_and_awake_is_clean() {
    let found = run("void Update() { Tick(); } void Tick() { var r = GetComponent<Rigidbody>(); }");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].rule, RULE_LOOKUP);
    assert!(found[0].message.contains("cache the result in Awake"));
    assert!(found[0].message.contains("Update"));
    assert!(rules("void Awake() { var r = GetComponent<Rigidbody>(); }").is_empty());
    assert!(rules("void Awake() { Setup(); } void Setup() { GetComponent<A>(); }").is_empty());
    assert_eq!(
        rules(
            "void Awake() { Setup(); } void Update() { Setup(); } void Setup() { GetComponent<A>(); }"
        ),
        [RULE_LOOKUP]
    );
}

// frob:tests crates/grimble-lints/src/unity_hot.rs::scan
#[test]
fn lookup_forms_and_receivers_are_recognised() {
    let all = "void Update() { this.GetComponent<A>(); other.gameObject.GetComponentInChildren<B>(); \
        GetComponent(typeof(C)); Object.FindObjectOfType<D>(); GameObject.Find(\"x\"); \
        transform.Find(\"y\"); var c = Camera.main; t?.GetComponent<E>(); \
        GameObject.FindWithTag(\"t\"); TryGetComponent(out a); }";
    assert_eq!(rules(all).len(), 10);
    assert!(rules("void Update() { items.Find(x => x > 1); var m = other.main; }").is_empty());
    assert_eq!(
        rules("void Update() { Foo(GetComponent<A>().GetComponent<B>()); }").len(),
        2
    );
}

// frob:tests crates/grimble-lints/src/unity_hot.rs::scan
#[test]
fn own_find_helper_is_followed_not_reported() {
    assert!(
        rules(
            "void Update() { FindObjectOfType<A>(); } T FindObjectOfType<T>() { return default; }"
        )
        .is_empty()
    );
    assert_eq!(
        rules("void Update() { Look<int>(); } void Look<T>() { GetComponent<T>(); }"),
        [RULE_LOOKUP]
    );
}

// frob:tests crates/grimble-lints/src/unity_hot.rs::scan
#[test]
fn new_list_in_fixed_update_fires_and_value_types_do_not() {
    let found = run("void FixedUpdate() { var l = new List<int>(); }");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].rule, RULE_ALLOC);
    assert_eq!(
        rules(
            "void LateUpdate() { var a = new int[4]; var d = new Dictionary<int, int>(); var s = new[] { 1 }; }"
        ),
        [RULE_ALLOC; 3]
    );
    assert!(
        rules("void Update() { var v = new Vector3(1, 2, 3); var e = new Enemy(); }").is_empty()
    );
    assert!(rules("void Start() { var l = new List<int>(); }").is_empty());
}

// frob:tests crates/grimble-lints/src/unity_hot.rs::scan
#[test]
fn target_typed_new_is_resolved_from_the_declaration() {
    assert_eq!(
        rules("void Update() { List<int> l = new(); }"),
        [RULE_ALLOC]
    );
    assert_eq!(rules("void Update() { cache = new(); }"), [RULE_ALLOC]);
    assert!(rules("void Update() { Vector3 v = new(); transform.position = new(); }").is_empty());
}

// frob:tests crates/grimble-lints/src/unity_hot.rs::scan
#[test]
fn lazy_field_caches_are_exempt() {
    assert!(rules("void Update() { if (cam == null) cam = Camera.main; }").is_empty());
    assert!(rules("void Update() { cam ??= Camera.main; cache ??= new List<int>(); }").is_empty());
    assert!(rules("void Update() { if (cache == null) { cache = new List<int>(); } }").is_empty());
    assert_eq!(rules("void Update() { cam = Camera.main; }"), [RULE_LOOKUP]);
    assert_eq!(
        rules("void Update() { if (cam == null) { var c = Camera.main; } }"),
        [RULE_LOOKUP]
    );
}

// frob:tests crates/grimble-lints/src/unity_hot.rs::scan
#[test]
fn non_hot_code_is_not_scanned() {
    assert!(
        rules("static void Update() { GetComponent<A>(); } IEnumerator Co() { GetComponent<A>(); yield return null; }")
            .is_empty()
    );
    assert_eq!(
        rules(
            "void Update() { StartCoroutine(Co()); } IEnumerator Co() { GetComponent<A>(); yield return null; }"
        ),
        Vec::<&str>::new()
    );
    let nested = "class O { class I { void Update() { GetComponent<A>(); } } void Awake() { GetComponent<A>(); } }";
    assert_eq!(scan(Language::CSharp, nested).expect("parses").len(), 1);
    assert!(
        scan(Language::Rust, "fn update() {}")
            .expect("ok")
            .is_empty()
    );
}
