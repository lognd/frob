import shutil
from pathlib import Path


class TestCapabilityScan:
    def test_scan_file_operations_names_registry_entry(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\nsubprocess.run(['ls'])\n")
        ops = _scan_file_operations(pkg)
        assert any(op.capability_kind == "exec" for op in ops)
        matched = next(op for op in ops if op.capability_kind == "exec")
        assert matched.library == "subprocess"
        assert matched.safer_alternative

    def test_scan_file_operations_no_language(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        assert _scan_file_operations(tmp_path / "foo.unknownext") == ()

    def test_scan_file_operations_bare_compile(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("code = compile(source, '<s>', 'exec')\n")
        ops = _scan_file_operations(pkg)
        assert any(op.function_or_pattern.startswith("compile(") for op in ops)

    def test_scan_file_operations_dotted_compile_not_matched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import re\n_RE = re.compile(r'^x$')\n")
        ops = _scan_file_operations(pkg)
        assert not any(op.function_or_pattern.startswith("compile(") for op in ops)

    def test_scan_file_operations_unreadable_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        missing = tmp_path / "gone.py"
        assert _scan_file_operations(missing) == ()

    def test_python_exec_and_net_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\nimport requests\nsubprocess.run(['ls'])\nrequests.get('x')\n"
        )
        capabilities = scan_file_capabilities(pkg)
        assert "exec" in capabilities
        assert "net-connect" in capabilities

    def test_rust_exec_detected(self, tmp_path: Path) -> None:
        from frob.vet._capability import scan_file_capabilities

        build_rs = tmp_path / "build.rs"
        build_rs.write_text('fn main() { std::process::Command::new("sh"); }\n')
        capabilities = scan_file_capabilities(build_rs)
        assert "exec" in capabilities

    def test_kotlin_net_okhttp_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0170: OkHttp is the dominant Android HTTP client -- one of the
        # per-cell fire fixtures for the new kotlin column.
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Client.kt"
        kt.write_text(
            "import okhttp3.OkHttpClient\nfun makeClient() = OkHttpClient()\n"
        )
        assert "net-connect" in scan_file_capabilities(kt)

    def test_kotlin_exec_runtime_exec_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Shell.kt"
        kt.write_text("fun run(cmd: String) {\n    Runtime.getRuntime().exec(cmd)\n}\n")
        assert "exec" in scan_file_capabilities(kt)

    def test_kotlin_client_storage_shared_preferences_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Prefs.kt"
        kt.write_text(
            "fun load(ctx: Context) {\n"
            '    val prefs = ctx.getSharedPreferences("app", 0)\n'
            "}\n"
        )
        assert "client_storage" in scan_file_capabilities(kt)

    def test_kotlin_benign_file_has_no_capabilities(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0170: a kotlin file that touches none of the patterned needles
        # observes an empty capability set -- confirms the column does not
        # over-fire on ordinary Kotlin code.
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Math.kt"
        kt.write_text("fun add(a: Int, b: Int): Int = a + b\n")
        assert scan_file_capabilities(kt) == frozenset()

    def test_c_source_exec_detected(self, tmp_path: Path) -> None:
        # T-0158: C/C++ is now a first-class scanned language (the old
        # blanket "honestly-empty" exemption is retired) -- system() is a
        # patterned c-cpp/exec _DangerousOperation.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text('int main() { system("ls"); return 0; }\n')
        assert "exec" in scan_file_capabilities(c_file)

    def test_c_source_fs_write_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: fopen/fwrite is the actual fs-write
        # surface -- the pre-existing strcpy-family entry is a memory-safety
        # bucket, not a real file write, so this used to scan as zero
        # capabilities.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(const char *path) {\n"
            '    FILE *fp = fopen(path, "w");\n'
            '    fwrite("x", 1, 1, fp);\n'
            "}\n"
        )
        assert "fs-write" in scan_file_capabilities(c_file)

    def test_c_source_raw_fd_read_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: open()/read() are the actual POSIX read
        # syscalls; only the buffered fread/fgets wrappers were patterned.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(const char *path) {\n"
            "    int fd = open(path, 0);\n"
            "    char buf[16];\n"
            "    read(fd, buf, sizeof(buf));\n"
            "}\n"
        )
        assert "fs-read" in scan_file_capabilities(c_file)

    def test_c_source_windows_exec_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: the exec table was POSIX-only; a
        # Windows-targeted dependency can launch a process via the Win32
        # API entirely, evading every prior needle.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(const char *cmd) {\n"
            '    ShellExecuteA(NULL, "open", cmd, NULL, NULL, 1);\n'
            "}\n"
        )
        assert "exec" in scan_file_capabilities(c_file)

    def test_c_source_net_recv_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: send/recv/getaddrinfo were entirely
        # absent from the net table.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(int fd) {\n"
            "    char buf[16];\n"
            "    recv(fd, buf, sizeof(buf), 0);\n"
            "}\n"
        )
        assert "net-connect" in scan_file_capabilities(c_file)

    def test_decode_to_exec_same_function(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_decode_to_exec_signal \
        # kind="unit"
        from frob.vet._capability_scan import _decode_to_exec_signal

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import base64\n"
            "def run(payload):\n"
            "    data = base64.b64decode(payload)\n"
            "    exec(data)\n"
        )
        assert _decode_to_exec_signal(pkg) is True

    def test_decode_to_exec_absent_when_separate(self, tmp_path: Path) -> None:
        from frob.vet._capability_scan import _decode_to_exec_signal

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import base64\n"
            "def decode(payload):\n"
            "    return base64.b64decode(payload)\n"
            "def other():\n"
            "    return 1\n"
        )
        assert _decode_to_exec_signal(pkg) is False

    def test_language_for_known_and_unknown_extensions(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_core.py::language_for kind="unit"
        from frob.vet._capability import language_for

        assert language_for(tmp_path / "mod.py") == "python"
        assert language_for(tmp_path / "mod.rs") == "rust"
        assert language_for(tmp_path / "mod.ts") == "typescript"
        # T-0158: C/C++ is now a first-class "c-cpp" bucket, not None.
        assert language_for(tmp_path / "mod.c") == "c-cpp"
        # T-0170: .kt/.kts extension mapping for the new kotlin column.
        assert language_for(tmp_path / "mod.kt") == "kotlin"
        assert language_for(tmp_path / "mod.kts") == "kotlin"
        # T-2906: .sh/.bash/.cs extension mapping for the new bash/csharp
        # columns.
        assert language_for(tmp_path / "mod.sh") == "bash"
        assert language_for(tmp_path / "mod.bash") == "bash"
        assert language_for(tmp_path / "mod.cs") == "csharp"
        # T-3492: .java extension mapping for the new java column.
        assert language_for(tmp_path / "Mod.java") == "java"
        # T-3493: .cu/.cuh extension mapping for the new cuda column.
        assert language_for(tmp_path / "mod.cu") == "cuda"
        assert language_for(tmp_path / "mod.cuh") == "cuda"
        assert language_for(tmp_path / "mod.unknownext") is None

    def test_bash_pipe_to_shell_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-2906: piping a downloaded script into a shell is bash's
        # highest-value fire fixture for the new bash column.
        from frob.vet._capability import scan_file_capabilities

        sh = tmp_path / "install.sh"
        sh.write_text("curl -fsSL https://example.com/install.sh | bash\n")
        capabilities = scan_file_capabilities(sh)
        assert "exec" in capabilities
        assert "fetch_url" in capabilities

    def test_bash_eval_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        sh = tmp_path / "run.sh"
        sh.write_text('cmd="$1"\neval $cmd\n')
        assert "eval" in scan_file_capabilities(sh)

    def test_bash_benign_file_has_no_capabilities(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-2906: a bash file that touches none of the patterned needles
        # observes an empty capability set -- confirms the column does not
        # over-fire on ordinary bash code (mirrors sample.sh, T-1604's own
        # walker fixture).
        from frob.vet._capability import scan_file_capabilities

        sh = tmp_path / "add.sh"
        sh.write_text("add() {\n    echo $(( $1 + $2 ))\n}\n")
        assert scan_file_capabilities(sh) == frozenset()

    def test_csharp_process_start_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-2906: Process.Start is csharp's highest-value fire fixture for
        # the new csharp column.
        from frob.vet._capability import scan_file_capabilities

        cs = tmp_path / "Shell.cs"
        cs.write_text(
            "using System.Diagnostics;\n"
            "class Shell {\n"
            "    void Run(string cmd) {\n"
            "        Process.Start(cmd);\n"
            "    }\n"
            "}\n"
        )
        assert "exec" in scan_file_capabilities(cs)

    def test_csharp_binary_formatter_deserialize_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        cs = tmp_path / "Loader.cs"
        cs.write_text(
            "using System.Runtime.Serialization.Formatters.Binary;\n"
            "class Loader {\n"
            "    object Load(System.IO.Stream s) {\n"
            "        var f = new BinaryFormatter();\n"
            "        return f.Deserialize(s);\n"
            "    }\n"
            "}\n"
        )
        assert "deserialize" in scan_file_capabilities(cs)

    def test_csharp_benign_file_has_no_capabilities(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-2906: a csharp file that touches none of the patterned needles
        # observes an empty capability set -- confirms the column does not
        # over-fire on ordinary C# code (mirrors sample.cs, T-1600's own
        # walker fixture).
        from frob.vet._capability import scan_file_capabilities

        cs = tmp_path / "Widget.cs"
        cs.write_text(
            "namespace Frob.Sample {\n"
            "    public class Widget {\n"
            "        public int Add(int a, int b) { return a + b; }\n"
            "    }\n"
            "}\n"
        )
        assert scan_file_capabilities(cs) == frozenset()

    def test_java_process_builder_exec_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-3492: ProcessBuilder is java's highest-value fire fixture for
        # the new java column.
        from frob.vet._capability import scan_file_capabilities

        java = tmp_path / "Shell.java"
        java.write_text(
            "import java.io.IOException;\n"
            "class Shell {\n"
            "    void run(String cmd) throws IOException {\n"
            "        new ProcessBuilder(cmd).start();\n"
            "    }\n"
            "}\n"
        )
        assert "exec" in scan_file_capabilities(java)

    def test_java_object_input_stream_deserialize_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        java = tmp_path / "Loader.java"
        java.write_text(
            "import java.io.ObjectInputStream;\n"
            "class Loader {\n"
            "    Object load(java.io.InputStream s) throws Exception {\n"
            "        ObjectInputStream in = new ObjectInputStream(s);\n"
            "        return in.readObject();\n"
            "    }\n"
            "}\n"
        )
        assert "deserialize" in scan_file_capabilities(java)

    def test_java_benign_file_has_no_capabilities(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-3492: a java file that touches none of the patterned needles
        # observes an empty capability set -- confirms the column does not
        # over-fire on ordinary Java code (mirrors T-1601's own walker
        # fixture posture).
        from frob.vet._capability import scan_file_capabilities

        java = tmp_path / "Widget.java"
        java.write_text(
            "package com.frob.sample;\n"
            "public class Widget {\n"
            "    public int add(int a, int b) { return a + b; }\n"
            "}\n"
        )
        assert scan_file_capabilities(java) == frozenset()

    def test_cuda_host_system_call_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-3493: system() is cuda's highest-value fire fixture (a .cu
        # file compiles with a host C++ compiler, same C ABI as c-cpp).
        from frob.vet._capability import scan_file_capabilities

        cu = tmp_path / "launcher.cu"
        cu.write_text(
            "#include <cstdlib>\n"
            'extern "C" void run(const char *cmd) {\n'
            "    system(cmd);\n"
            "}\n"
        )
        assert "exec" in scan_file_capabilities(cu)

    def test_cuda_dlopen_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        cu = tmp_path / "loader.cu"
        cu.write_text(
            "#include <dlfcn.h>\n"
            "void *load(const char *path) {\n"
            "    return dlopen(path, RTLD_NOW);\n"
            "}\n"
        )
        assert "ffi" in scan_file_capabilities(cu)

    def test_cuda_benign_kernel_has_no_capabilities(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-3493: a cuda kernel file that touches none of the patterned
        # needles observes an empty capability set -- confirms the column
        # does not over-fire on ordinary device kernel code.
        from frob.vet._capability import scan_file_capabilities

        cu = tmp_path / "add.cu"
        cu.write_text(
            "__global__ void add(int *a, int *b, int *c) {\n"
            "    int i = threadIdx.x;\n"
            "    c[i] = a[i] + b[i];\n"
            "}\n"
        )
        assert scan_file_capabilities(cu) == frozenset()

    def test_scan_directory_capabilities_aggregates_across_files(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_capabilities \
        # kind="unit"
        from frob.vet._capability_scan import _scan_directory_capabilities

        (tmp_path / "a.py").write_text("import subprocess\nsubprocess.run(['ls'])\n")
        (tmp_path / "b.py").write_text("import requests\nrequests.get('x')\n")
        capabilities, decode_to_exec_hit = _scan_directory_capabilities(tmp_path)
        assert "exec" in capabilities
        assert "net-connect" in capabilities
        assert decode_to_exec_hit is False

    def test_wrapper_capabilities_resolve_cross_file_via_call_graph(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_python.py::_python_wrapper_capabilities \
        # kind="unit"
        # T-1752: a private helper's dangerous call, reached only through a
        # call graph edge INTO ANOTHER FILE, must resolve symbolically --
        # never by matching the helper's name.
        from frob.vet._capability_core import _PATTERNS
        from frob.vet._capability_python import (
            _build_wrapper_call_graph,
            _python_wrapper_capabilities,
        )

        (tmp_path / "wrapper.py").write_text(
            "import subprocess\n\n\ndef _run_it(cmd):\n    return subprocess.run(cmd)\n"
        )
        (tmp_path / "caller.py").write_text(
            "from wrapper import _run_it\n\n\ndef do_thing(cmd):\n    return _run_it(cmd)\n"
        )
        graph = _build_wrapper_call_graph(tmp_path, ["caller.py", "wrapper.py"])
        found = _python_wrapper_capabilities(
            tmp_path / "caller.py", tmp_path, graph, _PATTERNS["python"]
        )
        assert "exec" in found

    def test_wrapper_capabilities_ignore_unrelated_cross_file_calls(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_python.py::_python_wrapper_capabilities \
        # kind="unit"
        # T-1752: a caller that reaches into another file WITHOUT ever
        # touching a dangerous target must not falsely attribute a
        # capability -- symbolic resolution, not "any cross-file call".
        from frob.vet._capability_core import _PATTERNS
        from frob.vet._capability_python import (
            _build_wrapper_call_graph,
            _python_wrapper_capabilities,
        )

        (tmp_path / "helper.py").write_text("def _add(a, b):\n    return a + b\n")
        (tmp_path / "caller.py").write_text(
            "from helper import _add\n\n\ndef do_thing(a, b):\n    return _add(a, b)\n"
        )
        graph = _build_wrapper_call_graph(tmp_path, ["caller.py", "helper.py"])
        found = _python_wrapper_capabilities(
            tmp_path / "caller.py", tmp_path, graph, _PATTERNS["python"]
        )
        assert found == set()

    # frob:ticket T-2223
    def test_public_sibling_wrapper_exec_is_resolved_one_hop(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_python.py::_python_local_wrapper_capabilities \
        # kind="unit"
        # MUST FAIL on current main: run() is PUBLIC (no leading
        # underscore), so T-1752's call graph never records an edge for
        # it (build_call_graph's own private-callee-only rule) and
        # scan_file_capabilities(b.py) returns frozenset().
        from frob.vet._capability import scan_file_capabilities

        (tmp_path / "a.py").write_text(
            "import os\n\n\ndef run(cmd):\n    os.system(cmd)\n"
        )
        (tmp_path / "b.py").write_text(
            "from a import run\n\n\ndef entry(x):\n    run(x)\n"
        )
        assert "exec" in scan_file_capabilities(tmp_path / "b.py")

    # frob:ticket T-2223
    def test_wrapper_with_no_dangerous_body_resolves_nothing(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_python.py::_python_local_wrapper_capabilities \
        # kind="unit"
        # Must-still-pass control: an ordinary public helper with no
        # dangerous call in its own body must not be falsely attributed
        # a capability just because it is imported and called.
        from frob.vet._capability import scan_file_capabilities

        (tmp_path / "helper.py").write_text("def add(a, b):\n    return a + b\n")
        (tmp_path / "caller.py").write_text(
            "from helper import add\n\n\ndef entry(a, b):\n    return add(a, b)\n"
        )
        assert scan_file_capabilities(tmp_path / "caller.py") == frozenset()

    # frob:ticket T-2223
    def test_wrapper_two_hops_away_is_not_followed(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/vet/_capability_python.py::_python_local_wrapper_capabilities \
        # kind="unit"
        # Honest limit, asserted directly: C imports from B, B imports
        # (and re-calls) from A where the real exec lives -- two hops
        # from C's own perspective. The one-hop resolver must not follow
        # this chain; this is the disclosed gap, not a false negative in
        # the one-hop case it DOES claim to cover.
        from frob.vet._capability import scan_file_capabilities

        (tmp_path / "a.py").write_text(
            "import os\n\n\ndef run(cmd):\n    os.system(cmd)\n"
        )
        (tmp_path / "b.py").write_text(
            "from a import run\n\n\ndef forward(cmd):\n    run(cmd)\n"
        )
        (tmp_path / "c.py").write_text(
            "from b import forward\n\n\ndef entry(x):\n    forward(x)\n"
        )
        assert scan_file_capabilities(tmp_path / "c.py") == frozenset()

    # frob:ticket T-2223
    def test_sibling_in_a_different_directory_is_not_followed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_python.py::_python_local_wrapper_capabilities \
        # kind="unit"
        # Honest limit, asserted directly: the one-hop resolver only
        # follows a SAME-DIRECTORY sibling, not frob.lang.resolve_local_
        # import's full package-root-aware resolution -- a package-
        # qualified import to a subdirectory module is a disclosed
        # remaining gap.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text("import os\n\n\ndef run(cmd):\n    os.system(cmd)\n")
        (tmp_path / "b.py").write_text(
            "from pkg.a import run\n\n\ndef entry(x):\n    run(x)\n"
        )
        assert scan_file_capabilities(tmp_path / "b.py") == frozenset()

    def test_re_compile_alone_does_not_report_eval(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0151: bare `compile(` used to match `re.compile(`/`ast.compile(`
        # dotted calls, spuriously reporting "eval" for ordinary regex code.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import re\nimport ast\n"
            "_RE = re.compile(r'^x$')\n"
            "tree = ast.compile('1', '<s>', 'eval')\n"
        )
        assert "eval" not in scan_file_capabilities(pkg)

    def test_bare_compile_call_still_reports_eval(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0151: the bare builtin `compile()` (not a dotted method access) is
        # a genuine eval-adjacent primitive and must still be caught.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("code = compile(source, '<s>', 'exec')\n")
        assert "eval" in scan_file_capabilities(pkg)

    def test_genuine_eval_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("eval(user_input)\n")
        assert "eval" in scan_file_capabilities(pkg)

    def test_comment_only_needle_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0209: pilot P2 -- a needle appearing only inside a `#` comment
        # describing forbidden network calls must not be reported as an
        # observation. The file's actual code never calls requests.get.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "starter.py"
        pkg.write_text(
            "# starter.py\n"
            "# Do not use requests.get() for real network calls here.\n"
            "def main():\n"
            "    pass\n"
        )
        assert "net" not in scan_file_capabilities(pkg)

    def test_real_code_needle_still_fires_alongside_comment(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0209: the comment-exclusion filter must not mask a genuine
        # needle hit elsewhere in real code, even when the same needle also
        # appears in a comment in the same file.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "real.py"
        pkg.write_text(
            "# calls requests.get under the hood\n"
            "import requests\n"
            "requests.get('http://example.com')\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_docstring_query_does_not_treat_enum_value_as_docstring(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_docstring_byte_spans_from_tree \
        # kind="unit"
        # T-1223: `_docstring_byte_spans_from_tree`'s tree-sitter Query
        # source matches the `expression_statement` SUPERTYPE, which also
        # conforms `assignment` nodes -- an ErrorSet-style class whose first
        # body statement is `NAME = "a string value"` must NOT be treated as
        # a class docstring (`_PY_DOC_CAPTURE_FILTER`'s parent-type check is
        # the fix; this reproduces the exact false-positive shape observed
        # against this repo's own `src/frob/exports/__init__.py`). A needle
        # written only inside that enum value must still fire as real code,
        # not be silently swallowed as if it were prose.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "errs.py"
        pkg.write_text(
            "from typani import ErrorSet\n\n\n"
            "class MyError(ErrorSet):\n"
            '    Bad = "subprocess.Popen(cmd)"\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_docstring_query_still_finds_real_docstrings(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_docstring_byte_spans_from_tree \
        # kind="unit"
        # T-1223 sibling of the enum-value regression test above: a genuine
        # module/class/function docstring containing the same needle must
        # still be excluded, exercising all three Query anchor patterns
        # (module, class body, function body) in one file.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "docs.py"
        pkg.write_text(
            '"""module doc: subprocess.Popen(cmd) is forbidden here."""\n\n\n'
            "class C:\n"
            '    """class doc: subprocess.Popen(cmd) too."""\n\n'
            "    def m(self):\n"
            '        """method doc: subprocess.Popen(cmd) as well."""\n'
            "        pass\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_string_literal_needle_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0209: only COMMENT spans are filtered -- a needle inside a string
        # literal (not a comment) is deliberately left unfiltered (module
        # docstring's T-0209 note: distinguishing exec-vector strings from
        # prose strings needs per-registry judgment this scanner lacks).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "stringy.py"
        pkg.write_text("cmd = 'requests.get(\"http://x\")'\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_capability_module_self_scan_documented_false_positive(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0151: the capability scanner's own source stores every needle as
        # literal string data, so scanning IT directly (not via directory
        # aggregation) still shows the accepted false-positive class
        # documented in the module docstring and docs/modules/vet.md -- this
        # locks that decision so a future "fix" doesn't silently change the
        # behavior either way.
        #
        # T-0769: the ORIGINAL "cmdclass"/"install-hook" instance of this
        # class no longer applies -- "cmdclass" only ever appeared inside
        # this module's own module-docstring PROSE (never as real table
        # data in this file; the actual DANGEROUS_OPERATIONS needle lives in
        # `_capability_registry.py`), and T-0769 now excludes docstring
        # spans from the raw-text scan the same way T-0209 already excludes
        # comment spans -- that is precisely the false-positive class T-0769
        # closes, not a regression of this one. The accepted false-positive
        # class this test locks still holds for genuine non-comment,
        # non-docstring CODE-level string literal data: `_has_bare_compile_
        # call`'s own `needle = b"compile("` bytes literal (a real code
        # statement, not prose) still makes this module observe "eval" on
        # itself, exactly the self-match class the module docstring
        # documents.
        #
        # T-1420 (portion 5): `_has_bare_compile_call` (and the rest of the
        # scanner-core primitives) moved to `_capability_core.py` in the
        # LARGE001 split -- the self-match now shows up scanning THAT file,
        # not the (now much smaller) `_capability.py` dispatcher, which no
        # longer carries this literal at all.
        from frob.vet._capability import scan_file_capabilities

        own_path = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "frob"
            / "vet"
            / "_capability_core.py"
        )
        capabilities = scan_file_capabilities(own_path)
        assert "eval" in capabilities  # b"compile(" appears as real code data
        assert "install-hook" not in capabilities  # T-0769: was docstring-only

    def test_scan_directory_capabilities_excludes_own_module(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_capabilities \
        # kind="unit"
        # T-0151: directory aggregation over vet's REAL package path must not
        # self-inflate "eval"/"exec" from _capability.py's own pattern-table
        # literals (its needle tuples contain "eval(", "subprocess.", etc as
        # data, and nowhere ELSE in src/frob/vet does real eval/exec-ish code
        # exist -- direct grep confirms zero non-_capability.py hits for
        # eval(/exec(/__import__(/importlib.import_module(). "install-hook"
        # is deliberately NOT asserted absent here: _ecosystem.py's genuine
        # cmdclass-detection logic contains the literal substring "cmdclass"
        # as its own check target, which is the separate, documented,
        # accepted false-positive class from the module docstring and
        # docs/modules/vet.md -- not something this exclusion targets.
        #
        # T-0253: the exclusion only fires when the scan root passed to
        # `_scan_directory_capabilities` itself identifies as frob's own
        # repo (`_is_frob_repo_root`, no ancestor search) -- scanning a bare
        # subdirectory like `src/frob/vet` directly no longer qualifies on
        # its own. Build a fake repo root carrying the pyproject-name +
        # crate-dir markers, with ONLY the real `vet/` package copied under
        # it (not the whole `src/frob` tree -- other packages like
        # `strata/_facts.py` have their OWN genuine, non-self-match eval
        # hits that would make a repo-wide assertion of "eval" absent
        # false; this test is specifically about vet/'s own self-match
        # exclusion, so it keeps the scan scoped the same way the pre-
        # T-0253 version did).
        from frob.vet._capability_scan import _scan_directory_capabilities

        repo_root = Path(__file__).resolve().parents[2]
        fake_repo = tmp_path / "self-scan"
        fake_repo.mkdir()
        (fake_repo / "pyproject.toml").write_text('[project]\nname = "frob"\n')
        (fake_repo / "frob-core").mkdir()
        (fake_repo / "strata-core").mkdir()
        shutil.copytree(
            repo_root / "src" / "frob" / "vet",
            fake_repo / "src" / "frob" / "vet",
            ignore=shutil.ignore_patterns("__pycache__"),
        )

        capabilities, _ = _scan_directory_capabilities(
            fake_repo / "src" / "frob" / "vet", max_files=500
        )
        assert "eval" in capabilities  # discriminator refuses a subdir scan root
        assert "exec" in capabilities

        capabilities_from_repo_root, _ = _scan_directory_capabilities(
            fake_repo, max_files=500
        )
        assert "eval" not in capabilities_from_repo_root
        assert "exec" not in capabilities_from_repo_root


class TestCapabilityScanBindingResolution:
    """T-0328: import/binding-aware symbol resolution -- the plain
    substring needle scan in `TestCapabilityScan` above is evadable by
    ordinary Python aliasing/from-import syntax (`import subprocess as sp`,
    `from subprocess import run`); these tests lock the fix's litmus: every
    evasion case now DETECTED, every shadowing case NOT detected (no false
    positives), and a bare unimported name never fires."""

    def test_import_as_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 1: `import subprocess as sp; sp.run(x)` -- the raw
        # text never contains "subprocess.run(" so the pre-T-0328 scanner
        # missed this entirely.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess as sp\nsp.run(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_from_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 2: `from subprocess import run; run(x)` -- a bare
        # call with no dotted prefix at the call site at all.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\nrun(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_from_import_as_detected_with_correct_kind(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Evasion case 3: `from os import system as e; e(x)` must resolve to
        # `os.system` -- capability "exec", NOT "eval" (the pre-T-0328
        # scanner reported nothing at all; a naive fix that just matched
        # "system" anywhere would have risked the wrong kind).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from os import system as e\ne('ls')\n")
        capabilities = scan_file_capabilities(pkg)
        assert "exec" in capabilities
        assert "eval" not in capabilities

    def test_import_as_alias_operation_names_registry_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: an aliased call
        # still names the real registry entry (library="subprocess"), not
        # just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess as sp\nsp.run(['ls'])\n")
        ops = _scan_file_operations(pkg)
        assert any(
            op.capability_kind == "exec" and op.library == "subprocess" for op in ops
        )

    def test_method_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a class method named `run` on an unrelated object
        # (`Job().run()`) must NOT resolve to a dangerous `run` symbol --
        # `Job()` is a call, not an import-bound name, so resolution
        # deliberately stops there.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("class Job:\n    def run(self):\n        pass\n\nJob().run()\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_param_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a function parameter named `system` shadows a
        # `from os import system` import for the duration of that function
        # -- calling the param must not resolve to `os.system`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from os import system\n\n\ndef g(system):\n    system('ls')\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_local_variable_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Shadow case: a local variable named `run` (assigned a harmless
        # value) shadows an imported dangerous `run` for the rest of that
        # function's scope.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "from subprocess import run\n\n\ndef f():\n"
            "    run = 'not a subprocess call'\n"
            "    run.upper()\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_bare_name_call_with_no_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No naive bare-name false positive: calling an undefined/locally-
        # scoped `run()` with no matching import anywhere in the file must
        # not resolve to anything.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("run('ls')\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_direct_call_still_detected_via_resolver(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Regression: an ordinary unaliased `subprocess.run()` call (already
        # caught by the raw-text scan) must still fire once the resolver
        # path is unioned in -- no regression on the common case.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\nsubprocess.run(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_attribute_only_env_access_via_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Non-call attribute access (no argument_list) through an aliased
        # import: `import os as o; o.environ` must resolve to `os.environ`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os as o\nx = o.environ\n")
        assert "env-read" in scan_file_capabilities(pkg)


class TestCapabilityScanLocalRebindResolution:
    """T-0337: follow-on to T-0328 -- the import/binding resolver above
    correctly resolves import ALIASES but does no intraprocedural
    dataflow, so a LOCAL rebinding of an already-imported dangerous name
    (`xyz = run; xyz(...)`) evaded the scan entirely. These tests lock the
    scope-local copy-propagation fix: single/chained/attribute rebinds now
    DETECTED, while every T-0328 no-false-positive/shadow guarantee
    (benign rebind, parameter shadow) stays silent."""

    def test_single_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `xyz = run; xyz(...)` -- a plain local rebind of an imported
        # dangerous name must resolve through the alias to "exec".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\nxyz = run\nxyz(['pwned'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `a = run; b = a; b(...)` -- transitive copy-propagation across
        # two hops in document order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\na = run\nb = a\nb(['pwned'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_attribute_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `e = os.system; e("x")` -- rebind to a dangerous ATTRIBUTE chain
        # (not a bare imported name) must also resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os\ne = os.system\ne('ls')\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_benign_rebind_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `run = lambda x: x; run()` -- a name that is never bound to any
        # dangerous target anywhere in the file must stay silent; a lambda
        # RHS is not a resolvable identifier/attribute chain, so it never
        # gets an alias-table entry.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("run = lambda x: x\nrun()\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_parameter_shadow_still_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0328 regression guard: a parameter named `run` shadowing an
        # imported dangerous `run` must stay silent -- a parameter binds no
        # alias-table entry (it is not an assignment RHS this pass ever
        # inspects), so the copy-propagation fix must not reopen this hole.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\n\n\ndef f(run):\n    run(['ls'])\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_dangerous_then_benign_rebind_stays_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Documented may-analysis over-approximation (T-0337): once a name
        # is EVER bound to a dangerous target in a scope, a later benign
        # reassignment of that same name does not clear the flag -- a call
        # anywhere in the scope through that name is still reported. This
        # is a deliberate soundness choice, not a bug: a flow-insensitive
        # "may" analysis over-approximates rather than risk a false
        # negative from tracking reassignment order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\nx = run\nx(['a'])\nx = 5\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_call_before_rebinding_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0468: Python sibling of the T-0378 Rust ordering fix. The
        # Python `_shadowing_scope`/`_py_scope_bound_names` pair collects
        # every name bound ANYWHERE in the enclosing scope with no byte-
        # position tracking, so a capability call textually BEFORE a
        # same-named rebind is wrongly treated as already shadowed and the
        # real dangerous call is silently dropped. `o.system(...)` here
        # executes before `o = None` takes effect (Python assignment does
        # not hoist), so it MUST still resolve through the `import os as o`
        # alias to "exec". Uses an ALIASED import (not bare `os.system`) so
        # the raw-text lexical pass cannot mask a resolver regression --
        # the raw source never contains the literal substring "os.system".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os as o\no.system('ls')\no = None\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_call_after_rebinding_still_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0468 sibling of the ordering test above: the position-aware
        # fix must not become unconditionally permissive -- a call AFTER
        # the same `o = None` rebind is still correctly shadowed.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os as o\no = None\no.system('ls')\n")
        assert "exec" not in scan_file_capabilities(pkg)


class TestCapabilityScanTaxonomyClosureResolution:
    """T-0659: closes the remaining Python static-resolvable gaps against
    docs/design/capability-evasion-taxonomy.md's denominator that T-0328/
    T-0337 left open -- chained assignment, tuple/starred destructuring,
    default-argument forwarding, attribute-target rebinding, star-import
    re-export (for a curated dangerous module), and order-independent
    conditional/try-except import-fallback aliasing. Every evasion case
    below is now DETECTED; the accompanying no-regression cases (a benign
    destructuring bind, a safe-only fallback) stay silent, matching the
    T-0328 no-false-positive posture."""

    def test_chained_assignment_outer_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `a = b = subprocess.run; a(x)` -- taxonomy "chained assignment".
        # The OUTER target (`a`) previously saw its RHS as an unresolvable
        # nested `assignment` node and gave up; `_resolve_py_expr` now
        # peels through it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\na = b = subprocess.run\na(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_assignment_inner_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Same source, calling through the INNER target (`b`) instead --
        # already worked pre-T-0659 (the plain single-assignment path), a
        # regression guard alongside the outer-target fix above.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\na = b = subprocess.run\nb(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_tuple_unpack_destructuring_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `f, g = subprocess.run, os.system; f(x)` -- taxonomy "tuple/list
        # unpacking bind", positional correspondence over the RHS literal.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess, os\nf, g = subprocess.run, os.system\nf(['x'])\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_tuple_unpack_second_element_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Same source, calling through the SECOND unpacked name -- proves
        # positional correspondence, not "first name always wins".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess, os\nf, g = subprocess.run, os.system\ng('x')\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_starred_unpack_leading_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `f, *rest = [subprocess.run]; f(x)` -- taxonomy "starred
        # unpacking bind"; `f` binds to the FIRST element regardless of how
        # many trailing elements the splat swallows.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\nf, *rest = [subprocess.run]\nf(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_starred_unpack_trailing_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `*rest, g = [1, subprocess.run]; g(x)` -- the splat-BEFORE case,
        # binding from the back of the sequence.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\n*rest, g = [1, subprocess.run]\ng(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_benign_destructuring_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No-false-positive guard: a destructuring bind whose RHS elements
        # are not resolvable (two lambdas) must stay silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("f, g = (lambda: 1), (lambda: 2)\nf()\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_default_arg_forwarding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `def h(cb=subprocess.run): cb(x)` -- taxonomy "default-arg
        # forwarding a callable".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\ndef h(cb=subprocess.run):\n    cb(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_attribute_target_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `mod.run = subprocess.run; mod.run(x)` -- taxonomy "attribute
        # rebinding" (best-effort, by-name object identity, documented on
        # `_attr_rebind_lookup`).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\n"
            "class Mod:\n    pass\n"
            "mod = Mod()\n"
            "mod.run = subprocess.run\n"
            "mod.run(['x'])\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_star_import_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # `from subprocess import *; run(x)` -- taxonomy "star-import
        # re-export chain", best-effort for a module `DANGEROUS_OPERATIONS`
        # curates (subprocess).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import *\nrun(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_star_import_untracked_module_not_claimed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No-false-positive/no-overclaim guard: a wildcard import of a
        # module NOT in `DANGEROUS_OPERATIONS` gets no best-effort binding
        # at all -- a bare `run(x)` with no matching import anywhere stays
        # silent (documented honest limitation, not a false resolution).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from some_untracked_pkg import *\nrun(['x'])\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_conditional_import_fallback_dangerous_first_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # taxonomy "conditional/try-except import fallback aliasing":
        # dangerous import in the `try` branch, benign fallback in
        # `except` -- the LATER (benign) binding must not silently
        # overwrite the dangerous one in the import table.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "try:\n"
            "    from os import system as run\n"
            "except ImportError:\n"
            "    from shlex import quote as run\n"
            "run('x')\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_conditional_import_fallback_dangerous_second_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Same construct with the branches swapped -- dangerous import
        # walked SECOND, proving the fix is order-independent, not just
        # "first wins" or "last wins" by coincidence of tree-walk order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "try:\n"
            "    from shlex import quote as run\n"
            "except ImportError:\n"
            "    from os import system as run\n"
            "run('x')\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_conditional_import_fallback_both_safe_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # No-false-positive guard: both fallback branches benign must stay
        # silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "try:\n"
            "    from shlex import quote as run\n"
            "except ImportError:\n"
            "    from textwrap import shorten as run\n"
            "run('x')\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_closure_capture_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "closure capture" row (Lang Ref 4.2 Naming and
        # binding): `def outer(): r = subprocess.run; def inner(): r(x);
        # return inner` -- the inner function's call to `r` must resolve
        # through the enclosing function's local binding.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\n"
            "def outer():\n"
            "    r = subprocess.run\n"
            "    def inner():\n"
            "        r(['ls'])\n"
            "    return inner\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_with_as_binding_a_callable_bearing_object_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "`as` in `with`/`except` binding a callable-
        # bearing object" row (Lang Ref 8.5 The with statement): the `as`
        # target of a `with` statement is part of the same bind family as
        # ordinary assignment -- `with open('x') as f: pass` is benign, but
        # `with contextlib.suppress(Exception) as e: r = e; r2 = getattr(e,
        # 'run', None)` illustrates the pattern is a genuine binding site.
        # The litmus below binds a dangerous callable through a `with ...
        # as` target directly and calls it inside the block.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\n"
            "import contextlib\n"
            "@contextlib.contextmanager\n"
            "def give_run():\n"
            "    yield subprocess.run\n"
            "with give_run() as r:\n"
            "    r(['ls'])\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_walrus_operator_bind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # T-0666: taxonomy "walrus operator bind" row (Lang Ref 6.12
        # Assignment expressions): `(f := subprocess.run)(x)` binds AND
        # calls in one expression.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\n(f := subprocess.run)(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)
