"""`_BASH_CSHARP_OPERATIONS`: the bash/csharp slice of
`DANGEROUS_OPERATIONS` (T-2906, T-1420 split precedent -- python and
typescript/rust/kotlin/c-cpp each already have their own file; bash+csharp
together pushed `_dangerous_ops_other.py` past the 800-line LARGE001
threshold, so they get this new file rather than a waiver that would
contradict that module's own "none is close to the threshold" docstring
claim)."""

from __future__ import annotations

from frob.vet._capability_registry._schemas import _DangerousOperation, _op

_BASH_CSHARP_OPERATIONS: tuple[_DangerousOperation, ...] = (
    # -- bash (T-2906): highest-value idioms only -- see _matrix.py's
    # `_new_adapter_matrix_excuses` for every other (kind, "bash") cell,
    # each with its own specific reason rather than a blanket exemption.
    _op(
        "bash",
        "builtins",
        "eval",
        "eval",
        "executes a string as shell code, including any interpolated untrusted input",
        "never eval untrusted input; use an array and call the command "
        "directly instead of building a string to eval",
        "critical",
        ("eval ", "eval\t", "eval$"),
        ("CWE-95",),
    ),
    _op(
        "bash",
        "pipe-to-shell",
        "curl|bash / wget|sh",
        "exec",
        "pipes a downloaded remote script directly into a shell "
        "interpreter with no integrity check",
        "download to a file, verify a checksum/signature, then execute",
        "critical",
        ("| bash", "|bash", "| sh", "|sh"),
        ("CWE-494",),
    ),
    _op(
        "bash",
        "curl/wget",
        "curl / wget",
        "fetch_url",
        "fetches a remote URL",
        "pin TLS verification on and avoid piping the response into a shell",
        "medium",
        ("curl ", "wget "),
        (),
    ),
    _op(
        "bash",
        "builtins",
        "rm -rf",
        "fs-write",
        "recursively removes a file tree with no confirmation",
        "scope the path narrowly and avoid unexpanded variables in the target path",
        "high",
        ("rm -rf ", "rm -fr "),
        ("CWE-732",),
    ),
    _op(
        "bash",
        "builtins",
        "source / .",
        "fs-read",
        "reads and executes another file's contents as shell code in the current shell",
        "source only files this script itself controls, never a "
        "user-writable or downloaded path",
        "high",
        ("source ", ". /"),
        ("CWE-829",),
    ),
    _op(
        "bash",
        "builtins",
        "export",
        "env-write",
        "mutates the process environment, visible to every child process "
        "spawned afterward",
        "scope environment mutation to the minimum needed and avoid exporting secrets",
        "low",
        ("export ",),
        (),
    ),
    _op(
        "bash",
        "builtins",
        "printenv",
        "env-read",
        "reads the process environment, a common secret-exfiltration vector",
        "read only the specific variable needed, never dump the whole "
        "environment to a log or remote endpoint",
        "low",
        ("printenv",),
        (),
    ),
    _op(
        "bash",
        "/dev/tcp",
        "/dev/tcp/HOST/PORT redirection",
        "net-connect",
        "opens a raw TCP socket via bash's /dev/tcp pseudo-device, no TLS "
        "and no certificate validation",
        "prefer curl/wget with TLS verification over a raw /dev/tcp socket",
        "medium",
        ("/dev/tcp/",),
        (),
    ),
    _op(
        "bash",
        "netcat",
        "nc -l",
        "net-listen",
        "binds and accepts inbound network connections",
        "bind only to a trusted interface and pin host/port explicitly",
        "medium",
        ("nc -l",),
        (),
    ),
    _op(
        "bash",
        "builtins",
        "kill",
        "process-control",
        "sends a signal to another process by pid",
        "prefer a supervisor's own stop mechanism over a raw signal to an "
        "externally-supplied pid",
        "medium",
        ("kill -9 ", "kill -KILL "),
        (),
    ),
    # -- csharp (T-2906): highest-value idioms only -- see _matrix.py's
    # `_new_adapter_matrix_excuses` for every other (kind, "csharp") cell.
    _op(
        "csharp",
        "System.Diagnostics",
        "Process.Start",
        "exec",
        "spawns an external process; a shell-invoking overload runs through cmd.exe/sh",
        "use ProcessStartInfo with UseShellExecute=false and an argument "
        "list, never a single interpolated command-line string",
        "high",
        ("Process.Start(",),
        ("CWE-78",),
    ),
    _op(
        "csharp",
        "System.CodeDom / Roslyn scripting",
        "CSharpScript.EvaluateAsync / CodeDomProvider",
        "eval",
        "compiles and executes a string as C# code at runtime",
        "never evaluate untrusted input as code",
        "critical",
        ("CSharpScript.", "CodeDomProvider."),
        ("CWE-95",),
    ),
    _op(
        "csharp",
        "System.Net.Http",
        "HttpClient.GetAsync / WebClient.DownloadString",
        "fetch_url",
        "fetches a remote URL",
        "validate the target host and enforce TLS certificate validation",
        "medium",
        ("HttpClient(", ".GetAsync(", "WebClient()"),
        (),
    ),
    _op(
        "csharp",
        "System.IO",
        "File.Delete / Directory.Delete(recursive: true)",
        "fs-write",
        "deletes a file or an entire directory tree",
        "scope the path narrowly and confirm it is not attacker-influenced",
        "high",
        ("Directory.Delete(", "File.Delete("),
        ("CWE-732",),
    ),
    _op(
        "csharp",
        "System.IO",
        "File.ReadAllText / File.ReadAllBytes",
        "fs-read",
        "reads a file's full contents from an attacker-influenceable path",
        "validate/normalize the path against an allow-listed base directory",
        "low",
        ("File.ReadAllText(", "File.ReadAllBytes("),
        (),
    ),
    _op(
        "csharp",
        "System",
        "Environment.SetEnvironmentVariable",
        "env-write",
        "mutates the process environment, visible to every child process "
        "spawned afterward",
        "scope environment mutation to the minimum needed and avoid "
        "storing secrets in it",
        "low",
        ("Environment.SetEnvironmentVariable(",),
        (),
    ),
    _op(
        "csharp",
        "System",
        "Environment.GetEnvironmentVariable",
        "env-read",
        "reads the process environment, a common secret-exfiltration vector",
        "read only the specific variable needed",
        "low",
        ("Environment.GetEnvironmentVariable(",),
        (),
    ),
    _op(
        "csharp",
        "System.Runtime.InteropServices",
        "DllImport / Marshal",
        "ffi",
        "calls into unmanaged native code across the P/Invoke boundary",
        "validate every marshaled value and avoid marshaling attacker-"
        "controlled buffers without a fixed size",
        "high",
        ("[DllImport(", "Marshal."),
        (),
    ),
    _op(
        "csharp",
        "System.Net.Sockets",
        "TcpClient / Socket",
        "net-connect",
        "opens a raw TCP socket to an attacker-influenceable host",
        "validate/allowlist the target host before connecting",
        "medium",
        ("new TcpClient(", "new Socket("),
        (),
    ),
    _op(
        "csharp",
        "System.Net",
        "TcpListener / HttpListener",
        "net-listen",
        "binds and accepts inbound network connections",
        "bind only to a trusted interface and pin host/port explicitly",
        "medium",
        ("new TcpListener(", "new HttpListener("),
        (),
    ),
    _op(
        "csharp",
        "System.Runtime.Serialization",
        "BinaryFormatter.Deserialize",
        "deserialize",
        "deserializes an untrusted byte stream with a formatter with no "
        "type allow-list -- a well-known .NET remote-code-execution vector",
        "use System.Text.Json or another type-safe serializer with a "
        "closed type set instead of BinaryFormatter",
        "critical",
        ("BinaryFormatter(", ".Deserialize("),
        ("CWE-502",),
    ),
)
