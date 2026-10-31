//! CAP001 for the Python process, network, environment, native-library, deserialization and
//! archive entry points (ticket 01M6422ZVVSTEKVMY0PR269X33, audit cases p15 to p19 and p25): each
//! registered entry point is reported certain through its import-resolved path, however imported;
//! a computed form is reported unresolved, never passed silently; a local object of the same name
//! is not a use.

// frob:ticket 01M6422ZVVSTEKVMY0PR269X33

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

fn bind_src(src: &str) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    std::fs::write(dir.path().join("src/x.py"), src).unwrap();
    let model = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n}\n";
    std::fs::write(dir.path().join("design/model.grmb"), model).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// (atom, certain) of every ungranted CAP001 finding.
fn cap001(src: &str) -> Vec<(String, bool)> {
    let b = bind_src(src);
    let mut v: Vec<_> = b
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001")
        .map(|f| {
            let atom = f.anchor.trim_start_matches("cap/node/a/");
            let atom = atom.split('/').next().unwrap_or(atom);
            (atom.to_owned(), f.reason.is_none())
        })
        .collect();
    v.sort();
    v.dedup();
    v
}

fn certain(src: &str, atom: &str) -> bool {
    let f = cap001(src);
    f.iter().any(|(a, c)| a == atom && *c)
}

fn run(cases: &[(&str, &str, &str)]) {
    for (name, atom, src) in cases {
        assert!(
            certain(src, atom),
            "{name}: expected certain {atom}, got {:?}",
            cap001(src)
        );
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_resolved
#[test]
fn p15_cap_os_exec_and_spawn_family() {
    let names = [
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        concat!("spawn", "ve"),
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
        "startfile",
        "popen",
        "system",
        "fork",
        "forkpty",
    ];
    for n in names {
        let direct = format!("import os\n\ndef go():\n    os.{n}('x')\n");
        let aliased = format!("import os as o\n\ndef go():\n    o.{n}('x')\n");
        let from = format!("from os import {n} as f\n\ndef go():\n    f('x')\n");
        for (form, src) in [("direct", direct), ("alias", aliased), ("from", from)] {
            assert!(
                certain(&src, "process.spawn"),
                "os.{n} {form}: {:?}",
                cap001(&src)
            );
        }
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_resolved
#[test]
fn p15_cap_pty_asyncio_subprocess_and_getoutput() {
    run(&[
        (
            "pty.spawn",
            "process.spawn",
            "import pty\n\ndef go():\n    pty.spawn('sh')\n",
        ),
        (
            "pty.fork",
            "process.spawn",
            "import pty\n\ndef go():\n    pty.fork()\n",
        ),
        (
            "create_subprocess_exec",
            "process.spawn",
            "import asyncio\n\nasync def go():\n    await asyncio.create_subprocess_exec('ls')\n",
        ),
        (
            "create_subprocess_shell",
            "process.spawn",
            "import asyncio\n\nasync def go():\n    await asyncio.create_subprocess_shell('ls')\n",
        ),
        (
            "from asyncio.subprocess",
            "process.spawn",
            "from asyncio.subprocess import create_subprocess_exec as c\n\nasync def go():\n    await c('ls')\n",
        ),
        (
            "getoutput",
            "process.spawn",
            "import subprocess as sp\n\ndef go():\n    sp.getoutput('ls')\n",
        ),
        (
            "getstatusoutput",
            "process.spawn",
            "from subprocess import getstatusoutput\n\ndef go():\n    getstatusoutput('ls')\n",
        ),
    ]);
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_resolved
#[test]
fn p16_cap_network_clients() {
    run(&[
        (
            "http.client",
            "net.connect",
            "import http.client\n\ndef go():\n    c = http.client.HTTPConnection('h')\n    c.request('GET', '/')\n",
        ),
        (
            "HTTPSConnection",
            "net.connect",
            "from http.client import HTTPSConnection as C\n\ndef go():\n    C('h')\n",
        ),
        (
            "urllib3 PoolManager",
            "net.connect",
            "import urllib3\n\ndef go():\n    urllib3.PoolManager().request('GET', 'u')\n",
        ),
        (
            "urllib3 request",
            "net.connect",
            "import urllib3\n\ndef go():\n    urllib3.request('GET', 'u')\n",
        ),
        (
            "urllib3 pool",
            "net.connect",
            "import urllib3\n\ndef go():\n    urllib3.HTTPSConnectionPool('h')\n",
        ),
        (
            "httpx get",
            "net.connect",
            "import httpx\n\ndef go():\n    httpx.get('u')\n",
        ),
        (
            "httpx post",
            "net.connect",
            "import httpx as h\n\ndef go():\n    h.post('u')\n",
        ),
        (
            "httpx stream",
            "net.connect",
            "from httpx import stream\n\ndef go():\n    stream('GET', 'u')\n",
        ),
        (
            "httpx Client",
            "net.connect",
            "import httpx\n\ndef go():\n    httpx.Client()\n",
        ),
        (
            "httpx AsyncClient",
            "net.connect",
            "import httpx\n\nasync def go():\n    async with httpx.AsyncClient() as c:\n        await c.get('u')\n",
        ),
        (
            "smtplib SMTP",
            "net.connect",
            "import smtplib\n\ndef go():\n    smtplib.SMTP('h')\n",
        ),
        (
            "smtplib SMTP_SSL",
            "net.connect",
            "from smtplib import SMTP_SSL\n\ndef go():\n    SMTP_SSL('h')\n",
        ),
        (
            "ftplib FTP",
            "net.connect",
            "import ftplib\n\ndef go():\n    ftplib.FTP('h')\n",
        ),
        (
            "ftplib FTP_TLS",
            "net.connect",
            "from ftplib import FTP_TLS as F\n\ndef go():\n    F('h')\n",
        ),
        (
            "open_connection",
            "net.connect",
            "import asyncio\n\nasync def go():\n    await asyncio.open_connection('h', 1)\n",
        ),
        (
            "open_unix_connection",
            "net.connect",
            "import asyncio\n\nasync def go():\n    await asyncio.open_unix_connection('p')\n",
        ),
        (
            "start_server",
            "net.listen",
            "import asyncio\n\nasync def go():\n    await asyncio.start_server(cb, 'h', 1)\n",
        ),
        (
            "start_unix_server",
            "net.listen",
            "from asyncio import start_unix_server\n\nasync def go():\n    await start_unix_server(cb, 'p')\n",
        ),
    ]);
}

// frob:tests crates/grimble-bind/src/caps.rs::names_callee
#[test]
fn p17_cap_environment_reads() {
    run(&[
        (
            "subscript",
            "env.read",
            "import os\n\ndef go():\n    return os.environ['HOME']\n",
        ),
        (
            "get",
            "env.read",
            "import os\n\ndef go():\n    return os.environ.get('HOME')\n",
        ),
        (
            "items",
            "env.read",
            "import os\n\ndef go():\n    return list(os.environ.items())\n",
        ),
        (
            "copy",
            "env.read",
            "import os\n\ndef go():\n    return os.environ.copy()\n",
        ),
        (
            "iterate",
            "env.read",
            "import os\n\ndef go():\n    for k in os.environ:\n        print(k)\n",
        ),
        (
            "from import",
            "env.read",
            "from os import environ\n\ndef go():\n    return environ['HOME']\n",
        ),
        (
            "alias",
            "env.read",
            "import os as o\n\ndef go():\n    return o.environ['HOME']\n",
        ),
        (
            "getenv",
            "env.read",
            "import os\n\ndef go():\n    return os.getenv('HOME')\n",
        ),
        (
            "getenv from",
            "env.read",
            "from os import getenv as g\n\ndef go():\n    return g('HOME')\n",
        ),
        (
            "environb",
            "env.read",
            "import os\n\ndef go():\n    return os.environb[b'HOME']\n",
        ),
        (
            "getenvb",
            "env.read",
            "import os\n\ndef go():\n    return os.getenvb(b'HOME')\n",
        ),
        (
            "unsetenv",
            "env.read",
            "import os\n\ndef go():\n    os.unsetenv('HOME')\n",
        ),
    ]);
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_resolved
#[test]
fn p18_cap_ctypes_loaders() {
    run(&[
        (
            "CDLL",
            "ffi",
            "import ctypes\n\ndef go():\n    ctypes.CDLL('libc.so.6')\n",
        ),
        (
            "from CDLL",
            "ffi",
            "from ctypes import CDLL as L\n\ndef go():\n    L('libc.so.6')\n",
        ),
        (
            "PyDLL",
            "ffi",
            "import ctypes\n\ndef go():\n    ctypes.PyDLL('x')\n",
        ),
        (
            "WinDLL",
            "ffi",
            "import ctypes\n\ndef go():\n    ctypes.WinDLL('x')\n",
        ),
        (
            "OleDLL",
            "ffi",
            "import ctypes\n\ndef go():\n    ctypes.OleDLL('x')\n",
        ),
        (
            "cdll.LoadLibrary",
            "ffi",
            "import ctypes\n\ndef go():\n    ctypes.cdll.LoadLibrary('x')\n",
        ),
        (
            "from cdll",
            "ffi",
            "from ctypes import cdll\n\ndef go():\n    cdll.LoadLibrary('x')\n",
        ),
        (
            "cdll attribute",
            "ffi",
            "import ctypes\n\ndef go():\n    return ctypes.cdll.libc\n",
        ),
        (
            "windll",
            "ffi",
            "import ctypes\n\ndef go():\n    return ctypes.windll.kernel32\n",
        ),
        (
            "find_library",
            "ffi",
            "import ctypes.util\n\ndef go():\n    return ctypes.util.find_library('c')\n",
        ),
        (
            "from util",
            "ffi",
            "from ctypes.util import find_library\n\ndef go():\n    return find_library('c')\n",
        ),
    ]);
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_resolved
#[test]
fn p25_cap_deserialization_loaders() {
    run(&[
        (
            "pickle.loads",
            "code.eval",
            "import pickle\n\ndef go(b):\n    return pickle.loads(b)\n",
        ),
        (
            "pickle.load",
            "code.eval",
            "import pickle\n\ndef go(f):\n    return pickle.load(f)\n",
        ),
        (
            "from loads",
            "code.eval",
            "from pickle import loads as l\n\ndef go(b):\n    return l(b)\n",
        ),
        (
            "Unpickler",
            "code.eval",
            "import pickle\n\ndef go(f):\n    return pickle.Unpickler(f).load()\n",
        ),
        (
            "_pickle",
            "code.eval",
            "import _pickle\n\ndef go(b):\n    return _pickle.loads(b)\n",
        ),
        (
            "marshal",
            "code.eval",
            "import marshal\n\ndef go(b):\n    return marshal.loads(b)\n",
        ),
        (
            "shelve",
            "code.eval",
            "import shelve\n\ndef go():\n    return shelve.open('db')\n",
        ),
        (
            "dill",
            "code.eval",
            "import dill\n\ndef go(b):\n    return dill.loads(b)\n",
        ),
        (
            "cloudpickle",
            "code.eval",
            "import cloudpickle\n\ndef go(b):\n    return cloudpickle.loads(b)\n",
        ),
    ]);
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p19_cap_archive_extraction() {
    run(&[
        (
            "tarfile extractall",
            "fs.write",
            "import tarfile\n\ndef go():\n    t = tarfile.open('a.tar')\n    t.extractall('d')\n",
        ),
        (
            "tarfile with extract",
            "fs.write",
            "import tarfile\n\ndef go():\n    with tarfile.open('a.tar') as t:\n        t.extract('m', 'd')\n",
        ),
        (
            "TarFile",
            "fs.write",
            "from tarfile import TarFile as T\n\ndef go():\n    t = T('a.tar')\n    t.extractall()\n",
        ),
        (
            "zipfile extractall",
            "fs.write",
            "import zipfile\n\ndef go():\n    with zipfile.ZipFile('a.zip') as z:\n        z.extractall('d')\n",
        ),
        (
            "zipfile extract",
            "fs.write",
            "from zipfile import ZipFile\n\ndef go():\n    ZipFile('a.zip').extract('m')\n",
        ),
        (
            "unpack_archive",
            "fs.write",
            "import shutil\n\ndef go():\n    shutil.unpack_archive('a.zip', 'd')\n",
        ),
        (
            "tarfile open reads",
            "fs.read",
            "import tarfile\n\ndef go():\n    tarfile.open('a.tar')\n",
        ),
    ]);
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_python_receivers
#[test]
fn p19_cap_untyped_archive_receiver_is_unresolved() {
    let f = cap001("import zipfile\n\ndef go(z):\n    z.extractall('d')\n");
    assert!(f.contains(&("fs.write".to_owned(), false)), "{f:?}");
    assert!(!f.contains(&("fs.write".to_owned(), true)), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_resolved
#[test]
fn p15_cap_computed_forms_are_unresolved_never_silent() {
    let f = cap001("import os\n\ndef go(n):\n    getattr(os, n)('x')\n");
    assert!(!f.is_empty(), "computed os attribute passed silently");
    assert!(f.iter().all(|(_, c)| !*c), "{f:?}");
    let f = cap001("import ctypes\n\ndef go(n):\n    getattr(ctypes, n)('x')\n");
    assert!(f.iter().any(|(a, c)| a == "ffi" && !*c), "{f:?}");
    let f = cap001("import importlib\n\ndef go(m):\n    importlib.import_module(m)\n");
    let _ = f;
}

// frob:tests crates/grimble-bind/src/caps.rs::scan_resolved
#[test]
fn p15_cap_local_objects_are_not_uses() {
    for src in [
        "def go(os):\n    return os.environ['X']\n",
        "class httpx:\n    @staticmethod\n    def get(u):\n        return u\n\ndef go():\n    httpx.get('u')\n",
        "def go(pickle):\n    return pickle.loads(b'')\n",
    ] {
        let f = cap001(src);
        assert!(f.iter().all(|(_, c)| !*c), "{src}: {f:?}");
    }
}
