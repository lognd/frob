"""`_DOTNET_BCL_OPERATIONS`: the .NET Base Class Library family map
(T-4511) -- csharp `_DangerousOperation` entries for BCL surface the
T-4536 csharp resolver's own highest-value-idioms slice
(`_dangerous_ops_bash_csharp.py`) does not already cover: `System.IO`
Directory/FileStream/StreamReader/StreamWriter family methods,
`System.Net.Sockets.Dns`, `System.Reflection` dynamic-load/-instantiate/
-typeresolve idioms, `Microsoft.Win32.Registry` key mutation, ADO.NET
`SqlCommand`/`DbCommand`, and `DataContractSerializer`/`JsonSerializer.
Deserialize`. Deliberately does NOT re-declare any needle already present
in `_dangerous_ops_bash_csharp.py`'s csharp slice (`Process.Start`,
`HttpClient`/`WebClient`, `File.WriteAllText`/`ReadAllText`, `Environment.
Get/SetEnvironmentVariable`, `DllImport`/`Marshal`, `TcpClient`/`Socket`,
`TcpListener`/`HttpListener`, `BinaryFormatter`) -- one entry per needle,
never two tables claiming the same API surface (NO DUPLICATION)."""

from __future__ import annotations

from frob.vet._capability_registry._schemas import _DangerousOperation, _op

_DOTNET_BCL_OPERATIONS: tuple[_DangerousOperation, ...] = (
    # -- System.IO: Directory family (T-4511) -------------------------------
    _op(
        "csharp",
        "System.IO",
        "Directory.CreateDirectory / Directory.Move",
        "fs-write",
        "creates or moves a directory tree at an attacker-influenceable path",
        "validate/normalize the path against an allow-listed base directory",
        "high",
        ("Directory.CreateDirectory(", "Directory.Move("),
        ("CWE-73",),
    ),
    _op(
        "csharp",
        "System.IO",
        "Directory.GetFiles / Directory.EnumerateFiles / "
        "Directory.EnumerateDirectories",
        "fs-read",
        "enumerates filesystem entries under an attacker-influenceable path",
        "validate/normalize the path against an allow-listed base directory",
        "low",
        (
            "Directory.GetFiles(",
            "Directory.EnumerateFiles(",
            "Directory.EnumerateDirectories(",
        ),
        (),
    ),
    # -- System.IO: FileStream/StreamReader/StreamWriter family (T-4511) ----
    _op(
        "csharp",
        "System.IO",
        "StreamReader",
        "fs-read",
        "reads a file's contents via a buffered stream reader from an "
        "attacker-influenceable path",
        "validate/normalize the path against an allow-listed base directory",
        "low",
        ("new StreamReader(",),
        (),
    ),
    _op(
        "csharp",
        "System.IO",
        "StreamWriter",
        "fs-write",
        "writes to a file via a buffered stream writer at an attacker-"
        "influenceable path, overwriting or appending its contents",
        "validate/normalize the path against an allow-listed base "
        "directory and avoid unbounded overwrite of caller-supplied paths",
        "high",
        ("new StreamWriter(",),
        ("CWE-73",),
    ),
    _op(
        "csharp",
        "System.IO",
        "FileStream / File.Open",
        "fs-write",
        "opens a raw file handle that can create, truncate, or write an "
        "attacker-influenceable path depending on the FileMode passed",
        "validate/normalize the path against an allow-listed base "
        "directory and pass the narrowest FileMode the call site needs",
        "high",
        ("new FileStream(", "File.Open("),
        ("CWE-73",),
    ),
    # -- System.Net.Sockets.Dns (T-4511) -------------------------------------
    _op(
        "csharp",
        "System.Net.Sockets",
        "Dns.GetHostAddresses / Dns.GetHostEntry / Dns.Resolve",
        # T-4511: "net-connect", NOT the bare "net" kind -- `_matrix.py`'s
        # `_STRUCTURAL_KIND_REASONS` generated excuse asserts "net" has no
        # scanner detection pattern of its own any more (T-0771's precise
        # net-connect/net-listen split); a DNS resolution is the same
        # connect-adjacent network-reach signal as the TcpClient/Socket
        # entries already in `_dangerous_ops_bash_csharp.py`, so it takes
        # their same precise kind rather than reviving the retired coarse one.
        "net-connect",
        "resolves an attacker-influenceable hostname over the network, a "
        "common SSRF-adjacent pivot point",
        "validate/allowlist the target hostname before resolving it",
        "medium",
        ("Dns.GetHostAddresses(", "Dns.GetHostEntry(", "Dns.Resolve("),
        (),
    ),
    # -- System.Reflection: dynamic-load/-instantiate/-typeresolve (T-4511) -
    _op(
        "csharp",
        "System.Reflection",
        "Assembly.Load / Assembly.LoadFrom / Assembly.LoadFile",
        "eval",
        "loads and executes an assembly's code at runtime, including one "
        "from an attacker-influenceable path or byte array",
        "never load an assembly from an untrusted source; pin to a "
        "known-good, signed assembly set",
        "critical",
        ("Assembly.Load(", "Assembly.LoadFrom(", "Assembly.LoadFile("),
        ("CWE-829",),
    ),
    _op(
        "csharp",
        "System",
        "Activator.CreateInstance(string typeName, ...)",
        "eval",
        "instantiates a type resolved from a runtime string name, "
        "including an attacker-influenceable one",
        "never resolve a type name from untrusted input; use a static "
        "type reference or a closed allow-list of type names",
        "high",
        ("Activator.CreateInstance(",),
        ("CWE-470",),
    ),
    _op(
        "csharp",
        "System",
        "Type.GetType(string typeName)",
        "eval",
        "resolves a Type from a runtime string name, the precondition for "
        "reflection-driven code execution against an attacker-"
        "influenceable type name",
        "never resolve a type name from untrusted input; use a static "
        "type reference or a closed allow-list of type names",
        "medium",
        ("Type.GetType(",),
        ("CWE-470",),
    ),
    # -- Microsoft.Win32.Registry (T-4511) -----------------------------------
    _op(
        "csharp",
        "Microsoft.Win32",
        "Registry.SetValue / RegistryKey.SetValue / Registry.CreateSubKey",
        "fs-write",
        "mutates a Windows registry key/value, a persistent machine- or "
        "user-scoped write with effects outside the process's own file tree",
        "validate/allowlist the target key path and avoid writing to "
        "machine-wide hives from an attacker-influenceable value",
        "high",
        (
            "Registry.SetValue(",
            "RegistryKey.SetValue(",
            "Registry.CreateSubKey(",
        ),
        ("CWE-732",),
    ),
    # -- System.Data: SqlCommand/DbCommand (T-4511) --------------------------
    _op(
        "csharp",
        "System.Data",
        "SqlCommand / DbCommand.ExecuteReader / ExecuteNonQuery / ExecuteScalar",
        "sql",
        "executes a SQL command; string-concatenated command text with "
        "attacker-influenceable input is a SQL-injection vector",
        "use a parameterized query (SqlParameter/DbParameter) instead of "
        "concatenating input into the command text",
        "high",
        (
            "new SqlCommand(",
            "DbCommand.ExecuteReader(",
            "DbCommand.ExecuteNonQuery(",
            "DbCommand.ExecuteScalar(",
        ),
        ("CWE-89",),
    ),
    # -- Deserialization: DataContractSerializer / JsonSerializer (T-4511) --
    _op(
        "csharp",
        "System.Runtime.Serialization",
        "DataContractSerializer.ReadObject",
        "deserialize",
        "deserializes an untrusted stream into a known type graph; a "
        "known-types list wider than needed still admits gadget chains",
        "constrain the known-types list to the minimum needed and never "
        "deserialize a stream from an untrusted source without validation",
        "high",
        ("new DataContractSerializer(",),
        ("CWE-502",),
    ),
    _op(
        "csharp",
        "System.Text.Json",
        "JsonSerializer.Deserialize",
        "deserialize",
        "deserializes untrusted JSON text into a CLR type; safer than a "
        "binary formatter by default but still a trust boundary when the "
        "target type or converter set is attacker-influenceable",
        "validate the input against an expected schema and avoid "
        "polymorphic/type-discriminator deserialization of untrusted input",
        "low",
        ("JsonSerializer.Deserialize(",),
        (),
    ),
)
