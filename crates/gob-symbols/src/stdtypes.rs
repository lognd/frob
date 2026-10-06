//! What the standard library says about a value's type: element types and method return types.
//!
//! A receiver known to be a `Vec<Foo>`, a `HashMap<K, V>`, an `Option<Foo>` or an iterator over
//! `Foo` types the values that flow out of `iter()`, `get(..)`, `unwrap_or(..)`, `enumerate()` and
//! friends. Soundness: only calls whose standard return type is certain are listed; a method not
//! listed, or a shape that is not fully known, gives `None` (the value stays untyped).

use crate::model::RetType;

/// The head of a tuple shape.
pub(crate) const TUPLE: &str = "(tuple)";
/// The head of an iterator shape: `arg` or `tuple` is its item.
pub(crate) const ITER: &str = "(iter)";
/// The head of a slice or array shape: `arg` is its element.
pub(crate) const SLICE: &str = "[]";

/// The head of a range expression (`a..b`): no repository type can be one.
pub(crate) const RANGE: &str = "(range)";
/// The head of a JSON-like value (`serde_json::Value`, `toml::Value`, `serde_yaml::Value`).
pub(crate) const JSON: &str = "(json)";
/// The head of an array of JSON-like values (`Vec<Value>`), standing for a `Vec` whose element is [`JSON`].
pub(crate) const JSON_ARRAY: &str = "(json[])";
/// The prefix of a trait-object head: `dyn:A+B` stands for `dyn A + B` (also `Box`/`Arc`/`Rc` of one).
pub(crate) const DYN: &str = "dyn:";

/// How a standard type is iterated and indexed.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Class {
    /// `Vec`, `VecDeque`, sets, slices: the first generic argument is the element.
    Seq,
    /// `HashMap`, `BTreeMap`: keys then values.
    Map,
    Option,
    Result,
    Iter,
    Str,
    Path,
    Json,
    Cell,
}

/// The standard class of `head`, if it is a standard type this module knows.
fn class(head: &str) -> Option<Class> {
    Some(match head {
        "Vec" | "VecDeque" | "HashSet" | "BTreeSet" | "BinaryHeap" | "LinkedList" | SLICE
        | JSON_ARRAY => Class::Seq,
        "HashMap" | "BTreeMap" => Class::Map,
        "Option" => Class::Option,
        "Result" => Class::Result,
        ITER => Class::Iter,
        "String" | "str" => Class::Str,
        "Path" | "PathBuf" | "OsStr" | "OsString" => Class::Path,
        JSON => Class::Json,
        "RefCell" | "Mutex" | "RwLock" => Class::Cell,
        _ => return None,
    })
}

/// True when `head` is a standard type with a method table (a repository type of that name must veto it).
pub(crate) fn is_std_head(head: &str) -> bool {
    class(head).is_some()
}

/// A shape with just a head.
fn bare(head: &str) -> RetType {
    RetType {
        head: head.to_owned(),
        arg: None,
        arg2: None,
        tuple: None,
    }
}

/// `head<inner>`: the shape `inner` wrapped in the generic type `head` (a tuple `inner` is kept as elements).
pub(crate) fn wrap(head: &str, inner: &RetType) -> RetType {
    let tuple = inner.head == TUPLE;
    RetType {
        head: head.to_owned(),
        arg: (!tuple).then(|| inner.head.clone()),
        arg2: None,
        tuple: tuple.then(|| inner.tuple.clone()).flatten(),
    }
}

/// A tuple shape of plain element heads.
fn tuple_of(elems: Vec<Option<String>>) -> RetType {
    RetType {
        head: TUPLE.to_owned(),
        arg: None,
        arg2: None,
        tuple: Some(elems),
    }
}

/// The first generic argument of `s` as a shape (`Foo` in `Vec<Foo>`, the tuple in `Option<(A, B)>`).
pub(crate) fn inner(s: &RetType) -> Option<RetType> {
    if s.head == JSON_ARRAY {
        return Some(bare(JSON));
    }
    match (&s.arg, &s.tuple) {
        (Some(a), _) if a != "Self" => Some(bare(a)),
        (None, Some(t)) if s.head != TUPLE => Some(tuple_of(t.clone())),
        _ => None,
    }
}

/// The second generic argument of `s` as a shape (`V` in `HashMap<K, V>`).
fn second(s: &RetType) -> Option<RetType> {
    s.arg2.as_deref().filter(|a| *a != "Self").map(bare)
}

/// The item that iterating `s` (`for x in s`) yields.
pub(crate) fn item_of(s: &RetType) -> Option<RetType> {
    match class(&s.head)? {
        Class::Seq | Class::Option | Class::Result | Class::Iter => inner(s),
        Class::Map => Some(tuple_of(vec![s.arg.clone(), s.arg2.clone()])),
        Class::Str | Class::Path | Class::Json | Class::Cell => None,
    }
}

/// The element `s[i]` for a non-range index `i`.
pub(crate) fn index_of(s: &RetType) -> Option<RetType> {
    match (class(&s.head)?, s.head.as_str()) {
        (Class::Seq, "Vec" | "VecDeque" | SLICE | JSON_ARRAY) => inner(s),
        (Class::Map, _) => second(s),
        (Class::Json, _) => Some(bare(JSON)),
        _ => None,
    }
}

/// The methods the standard derive `derive` generates (`Clone` gives `clone`, `Default` gives `default`).
pub(crate) fn std_derive_methods(derive: &str) -> &'static [&'static str] {
    match derive {
        "Clone" => &["clone", "clone_from"],
        "Default" => &["default"],
        "Debug" => &["fmt"],
        "PartialEq" => &["eq", "ne"],
        "PartialOrd" => &["partial_cmp", "lt", "le", "gt", "ge"],
        "Ord" => &["cmp", "max", "min", "clamp"],
        "Hash" => &["hash"],
        "Serialize" => &["serialize"],
        "Deserialize" => &["deserialize"],
        _ => &[],
    }
}

/// True for a collection `collect` can build item-by-item from an iterator.
pub(crate) fn is_collection(head: &str) -> bool {
    matches!(
        head,
        "Vec" | "VecDeque" | "HashSet" | "BTreeSet" | "BinaryHeap" | "HashMap" | "BTreeMap"
    )
}

/// The collection `head` built by collecting an iterator of `item`s (a map needs `(key, value)` tuples).
pub(crate) fn collect_into(head: &str, item: &RetType) -> Option<RetType> {
    match head {
        "HashMap" | "BTreeMap" => {
            let [k, v] = item.tuple.as_deref()? else {
                return None;
            };
            Some(RetType {
                head: head.to_owned(),
                arg: k.clone(),
                arg2: v.clone(),
                tuple: None,
            })
        }
        "Vec" | "VecDeque" | "HashSet" | "BTreeSet" | "BinaryHeap" => Some(wrap(head, item)),
        _ => None,
    }
}

/// The shape of `s.name(..)` with `args` arguments, for a standard `s` and a method of known return type.
pub(crate) fn step(s: &RetType, name: &str, args: usize) -> Option<RetType> {
    let class = class(&s.head)?;
    if args == 0 && (name == "clone" || (name == "to_owned" && class != Class::Str)) {
        return Some(s.clone());
    }
    match class {
        Class::Seq => seq_step(s, name),
        Class::Map => map_step(s, name),
        Class::Option => option_step(s, name),
        Class::Result => result_step(s, name),
        Class::Iter => iter_step(s, name),
        Class::Str => str_step(name),
        Class::Path => path_step(name),
        Class::Json => json_step(name),
        Class::Cell => cell_step(s, name),
    }
}

/// Methods of `Vec`, slices and sets.
fn seq_step(s: &RetType, name: &str) -> Option<RetType> {
    let item = inner(s)?;
    Some(match name {
        "iter" | "iter_mut" | "into_iter" | "drain" => wrap(ITER, &item),
        "first" | "last" | "first_mut" | "last_mut" | "pop" | "pop_front" | "pop_back"
        | "front" | "back" | "front_mut" | "back_mut" | "peek" | "get" | "get_mut" => {
            wrap("Option", &item)
        }
        "to_vec" => wrap("Vec", &item),
        "as_slice" | "as_mut_slice" => wrap(SLICE, &item),
        _ => return None,
    })
}

/// Methods of `HashMap` and `BTreeMap`.
fn map_step(s: &RetType, name: &str) -> Option<RetType> {
    let key = || s.arg.as_deref().filter(|a| *a != "Self").map(bare);
    Some(match name {
        "iter" | "iter_mut" | "into_iter" | "drain" => {
            wrap(ITER, &tuple_of(vec![s.arg.clone(), s.arg2.clone()]))
        }
        "keys" | "into_keys" => wrap(ITER, &key()?),
        "values" | "values_mut" | "into_values" => wrap(ITER, &second(s)?),
        "get" | "get_mut" | "remove" => wrap("Option", &second(s)?),
        _ => return None,
    })
}

/// Methods of `Option`.
fn option_step(s: &RetType, name: &str) -> Option<RetType> {
    let item = inner(s)?;
    Some(match name {
        "as_ref" | "as_mut" | "cloned" | "copied" | "take" | "or" | "or_else" | "xor"
        | "filter" | "replace" => s.clone(),
        "unwrap" | "expect" | "unwrap_or" | "unwrap_or_else" | "unwrap_or_default" => item,
        "as_deref" => match item.head.as_str() {
            "String" => wrap("Option", &bare("str")),
            "PathBuf" => wrap("Option", &bare("Path")),
            _ => return None,
        },
        "ok_or" | "ok_or_else" => wrap("Result", &item),
        "iter" | "iter_mut" | "into_iter" => wrap(ITER, &item),
        _ => return None,
    })
}

/// Methods of `Result`.
fn result_step(s: &RetType, name: &str) -> Option<RetType> {
    let item = inner(s)?;
    Some(match name {
        "ok" => wrap("Option", &item),
        "as_ref" | "as_mut" | "map_err" | "or_else" | "or" => wrap("Result", &item),
        "unwrap" | "expect" | "unwrap_or" | "unwrap_or_else" | "unwrap_or_default" => item,
        "iter" | "iter_mut" | "into_iter" => wrap(ITER, &item),
        _ => return None,
    })
}

/// Methods of an iterator over `inner(s)`.
fn iter_step(s: &RetType, name: &str) -> Option<RetType> {
    let item = inner(s)?;
    Some(match name {
        "filter" | "rev" | "skip" | "take" | "skip_while" | "take_while" | "peekable"
        | "cloned" | "copied" | "by_ref" | "inspect" | "step_by" | "fuse" | "cycle" | "chain"
        | "into_iter" => s.clone(),
        "enumerate" => wrap(
            ITER,
            &tuple_of(vec![
                Some("usize".to_owned()),
                (item.head != TUPLE).then(|| item.head.clone()),
            ]),
        ),
        "next" | "last" | "nth" | "min" | "max" | "find" | "next_back" | "min_by_key"
        | "max_by_key" | "min_by" | "max_by" | "reduce" | "peek" => wrap("Option", &item),
        _ => return None,
    })
}

/// Methods of a JSON-like value with a certain return type (`v["a"]`, `v.get("a")`, `v.as_array()`).
fn json_step(name: &str) -> Option<RetType> {
    Some(match name {
        "get" | "get_mut" | "pointer" => wrap("Option", &bare(JSON)),
        "as_array" | "as_array_mut" => wrap("Option", &bare(JSON_ARRAY)),
        "as_str" => wrap("Option", &bare("str")),
        _ => return None,
    })
}

/// The type of the field `field` of the standard struct `head` (`Output::status`), when it is a plain type.
pub(crate) fn ext_field(head: &str, field: &str) -> Option<RetType> {
    Some(match (head, field) {
        ("Output", "status") => bare("ExitStatus"),
        ("Output", "stdout" | "stderr") => wrap("Vec", &bare("u8")),
        _ => return None,
    })
}

/// True when `path` is a JSON-like value type of a well-known external crate.
pub(crate) fn is_json_path(path: &str) -> bool {
    matches!(
        path,
        "serde_json::Value" | "toml::Value" | "serde_yaml::Value" | "serde_yaml_ng::Value"
    )
}

/// Methods of `RefCell`, `Mutex` and `RwLock`: the borrowed or locked value is the first generic argument.
fn cell_step(s: &RetType, name: &str) -> Option<RetType> {
    let item = inner(s)?;
    match (s.head.as_str(), name) {
        ("RefCell", "borrow" | "borrow_mut" | "into_inner") => Some(item),
        ("Mutex" | "RwLock", "lock" | "read" | "write" | "try_lock" | "into_inner") => {
            Some(wrap("Result", &item))
        }
        _ => None,
    }
}

/// Methods of `Path`, `PathBuf` and `OsStr` with a certain return type.
fn path_step(name: &str) -> Option<RetType> {
    Some(match name {
        "parent" => wrap("Option", &bare("Path")),
        "join" | "to_path_buf" | "with_extension" | "with_file_name" | "to_owned" => {
            bare("PathBuf")
        }
        "as_path" => bare("Path"),
        "file_name" | "extension" | "file_stem" => wrap("Option", &bare("OsStr")),
        "to_str" => wrap("Option", &bare("str")),
        "to_string_lossy" => bare("str"),
        "ancestors" => wrap(ITER, &bare("Path")),
        _ => return None,
    })
}

/// The standard function or associated function `path::name` (`fs::read_to_string`, `String::from_utf8`), by its last path segment.
pub(crate) fn assoc_fn(module: &str, name: &str) -> Option<RetType> {
    let result = |t: &str| wrap("Result", &bare(t));
    Some(match (module, name) {
        ("fs", "read_to_string") | ("env", "var") | ("String", "from_utf8") => result("String"),
        ("fs", "read") => result("Vec"),
        ("fs", "read_dir") => result("ReadDir"),
        ("fs", "canonicalize") | ("env", "current_dir") => result("PathBuf"),
        ("env", "args") => wrap(ITER, &bare("String")),
        ("String", "from_utf8_lossy") => bare("str"),
        ("Path", "new") => bare("Path"),
        ("PathBuf", "from" | "new") => bare("PathBuf"),
        ("str", "from_utf8") => result("str"),
        _ => return None,
    })
}

/// Methods of `String` and `str` with a certain return type.
fn str_step(name: &str) -> Option<RetType> {
    Some(match name {
        "lines"
        | "split"
        | "rsplit"
        | "splitn"
        | "rsplitn"
        | "split_whitespace"
        | "split_terminator"
        | "split_ascii_whitespace"
        | "split_inclusive"
        | "matches" => wrap(ITER, &bare("str")),
        "as_bytes" => wrap(SLICE, &bare("u8")),
        "chars" => wrap(ITER, &bare("char")),
        "bytes" => wrap(ITER, &bare("u8")),
        "char_indices" => wrap(
            ITER,
            &tuple_of(vec![Some("usize".to_owned()), Some("char".to_owned())]),
        ),
        "trim" | "trim_start" | "trim_end" | "trim_matches" | "trim_start_matches"
        | "trim_end_matches" | "as_str" => bare("str"),
        "strip_prefix" | "strip_suffix" | "get" => wrap("Option", &bare("str")),
        "split_once" | "rsplit_once" => RetType {
            head: "Option".to_owned(),
            arg: None,
            arg2: None,
            tuple: Some(vec![Some("str".to_owned()), Some("str".to_owned())]),
        },
        "to_string" | "to_owned" | "into_owned" | "to_lowercase" | "to_uppercase" | "replace"
        | "repeat" | "to_ascii_lowercase" | "to_ascii_uppercase" => bare("String"),
        _ => return None,
    })
}

// frob:ticket 01M44YQTCDPH87ASRMSJEN2C8Q

/// True when `name` is a C# keyword type (`string`, `int`, `object`, ...): always the BCL, never a repository type.
pub(crate) fn is_dotnet_keyword_type(name: &str) -> bool {
    matches!(
        name,
        "string"
            | "object"
            | "bool"
            | "byte"
            | "sbyte"
            | "char"
            | "short"
            | "ushort"
            | "int"
            | "uint"
            | "long"
            | "ulong"
            | "float"
            | "double"
            | "decimal"
            | "nint"
            | "nuint"
            | "dynamic"
    )
}

/// True when `name` is a .NET core library type that is unambiguous across engines (a repository type of that name must veto it).
pub(crate) fn is_dotnet_core_type(name: &str) -> bool {
    matches!(
        name,
        "Console"
            | "Math"
            | "String"
            | "Convert"
            | "Enumerable"
            | "List"
            | "Dictionary"
            | "HashSet"
            | "Queue"
            | "Stack"
            | "SortedDictionary"
            | "KeyValuePair"
            | "Tuple"
            | "Task"
            | "File"
            | "Path"
            | "Directory"
            | "Environment"
            | "Guid"
            | "DateTime"
            | "TimeSpan"
            | "StringBuilder"
            | "Array"
            | "Buffer"
            | "Activator"
            | "Interlocked"
            | "Monitor"
            | "Exception"
            | "ArgumentException"
            | "ArgumentNullException"
            | "ArgumentOutOfRangeException"
            | "InvalidOperationException"
            | "NotImplementedException"
            | "NotSupportedException"
            | "KeyNotFoundException"
            | "IOException"
            | "StringComparer"
            | "Regex"
    )
}

/// True when `root` begins a .NET framework namespace (`System.Linq`, `Microsoft.Extensions`).
pub(crate) fn is_dotnet_namespace_root(root: &str) -> bool {
    matches!(root, "System" | "Microsoft")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn vec_of(t: &str) -> RetType {
        RetType {
            head: "Vec".into(),
            arg: Some(t.into()),
            arg2: None,
            tuple: None,
        }
    }

    #[test]
    fn iter_yields_the_element() {
        let it = step(&vec_of("Foo"), "iter", 0).expect("iter");
        assert_eq!(it.head, ITER);
        assert_eq!(item_of(&it).expect("item").head, "Foo");
    }

    #[test]
    fn enumerate_yields_a_tuple_of_index_and_element() {
        let it = step(&vec_of("Foo"), "iter", 0).and_then(|i| step(&i, "enumerate", 0));
        let item = item_of(&it.expect("enumerate")).expect("item");
        assert_eq!(item.head, TUPLE);
        assert_eq!(
            item.tuple,
            Some(vec![Some("usize".to_owned()), Some("Foo".to_owned())])
        );
    }

    #[test]
    fn unknown_methods_and_untyped_elements_stay_untyped() {
        assert!(step(&vec_of("Foo"), "frobnicate", 0).is_none());
        let bare_vec = bare("Vec");
        assert!(step(&bare_vec, "iter", 0).is_none());
        assert!(item_of(&bare_vec).is_none());
    }

    #[test]
    fn map_values_and_keys() {
        let m = RetType {
            head: "HashMap".into(),
            arg: Some("K".into()),
            arg2: Some("V".into()),
            tuple: None,
        };
        let vals = step(&m, "values", 0).expect("values");
        assert_eq!(item_of(&vals).expect("item").head, "V");
        let keys = step(&m, "keys", 0).expect("keys");
        assert_eq!(item_of(&keys).expect("item").head, "K");
        assert_eq!(index_of(&m).expect("index").head, "V");
    }
}
