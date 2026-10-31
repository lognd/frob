//! Capability vocabularies for the TypeScript family (TypeScript, JavaScript, Node, Deno, Bun) and
//! C#: the resolved callee paths that spawn a process, touch the filesystem or network, read the
//! environment or evaluate code (ticket PKW7X2J).
//!
//! Names are the symbolic paths `lookups` resolves through each language's import system, so
//! `import * as cp from "node:child_process"; cp.exec(x)` and `using P = System.Diagnostics.Process;
//! P.Start(x)` both spell `child_process.exec` and `System.Diagnostics.Process.Start`. A `node:`
//! prefix is stripped before matching. Scope: grimble-bind matches these against resolved paths
//! only, never against spelled text, so a local `fs` object names nothing.

// frob:ticket 01M642307T98S89GQ4APKW7X2J
// frob:ticket 01M64230AR8DHJZY9QQS3EC85S
// frob:ticket 01M6422ZVVSTEKVMY0PR269X33

use gob_ir::VocabEntry;

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "process.spawn", names: &[
        "child_process.exec", "child_process.execSync", "child_process.execFile",
        "child_process.execFileSync", "child_process.spawn", "child_process.spawnSync",
        "child_process.fork", "Deno.run", "Deno.Command", "Bun.spawn", "Bun.spawnSync",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "fs.read", names: &[
        "fs.readFile", "fs.promises.readFile", "fs/promises.readFile", "fs.readFileSync",
        "fs.promises.readFileSync", "fs/promises.readFileSync", "fs.readdir",
        "fs.promises.readdir", "fs/promises.readdir", "fs.readdirSync",
        "fs.promises.readdirSync", "fs/promises.readdirSync", "fs.readlink",
        "fs.promises.readlink", "fs/promises.readlink", "fs.readlinkSync",
        "fs.promises.readlinkSync", "fs/promises.readlinkSync", "fs.stat", "fs.promises.stat",
        "fs/promises.stat", "fs.statSync", "fs.promises.statSync", "fs/promises.statSync",
        "fs.lstat", "fs.promises.lstat", "fs/promises.lstat", "fs.lstatSync",
        "fs.promises.lstatSync", "fs/promises.lstatSync", "fs.access", "fs.promises.access",
        "fs/promises.access", "fs.accessSync", "fs.promises.accessSync",
        "fs/promises.accessSync", "fs.exists", "fs.promises.exists", "fs/promises.exists",
        "fs.existsSync", "fs.promises.existsSync", "fs/promises.existsSync", "fs.open",
        "fs.promises.open", "fs/promises.open", "fs.openSync", "fs.promises.openSync",
        "fs/promises.openSync", "fs.opendir", "fs.promises.opendir", "fs/promises.opendir",
        "fs.opendirSync", "fs.promises.opendirSync", "fs/promises.opendirSync",
        "fs.createReadStream", "fs.promises.createReadStream", "fs/promises.createReadStream",
        "fs.realpath", "fs.promises.realpath", "fs/promises.realpath", "fs.realpathSync",
        "fs.promises.realpathSync", "fs/promises.realpathSync", "fs.readv", "fs.promises.readv",
        "fs/promises.readv", "fs.readvSync", "fs.promises.readvSync", "fs/promises.readvSync",
        "fs.watch", "fs.promises.watch", "fs/promises.watch", "fs.watchFile",
        "fs.promises.watchFile", "fs/promises.watchFile", "fs.glob", "fs.promises.glob",
        "fs/promises.glob", "fs.globSync", "fs.promises.globSync", "fs/promises.globSync",
        "Deno.readTextFile", "Deno.readFile", "Deno.readDir", "Deno.stat", "Deno.lstat",
        "Deno.open", "Deno.readLink", "Deno.realPath", "Bun.file",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "fs.write", names: &[
        "fs.writeFile", "fs.promises.writeFile", "fs/promises.writeFile", "fs.writeFileSync",
        "fs.promises.writeFileSync", "fs/promises.writeFileSync", "fs.appendFile",
        "fs.promises.appendFile", "fs/promises.appendFile", "fs.appendFileSync",
        "fs.promises.appendFileSync", "fs/promises.appendFileSync", "fs.mkdir",
        "fs.promises.mkdir", "fs/promises.mkdir", "fs.mkdirSync", "fs.promises.mkdirSync",
        "fs/promises.mkdirSync", "fs.mkdtemp", "fs.promises.mkdtemp", "fs/promises.mkdtemp",
        "fs.mkdtempSync", "fs.promises.mkdtempSync", "fs/promises.mkdtempSync", "fs.rm",
        "fs.promises.rm", "fs/promises.rm", "fs.rmSync", "fs.promises.rmSync",
        "fs/promises.rmSync", "fs.rmdir", "fs.promises.rmdir", "fs/promises.rmdir",
        "fs.rmdirSync", "fs.promises.rmdirSync", "fs/promises.rmdirSync", "fs.unlink",
        "fs.promises.unlink", "fs/promises.unlink", "fs.unlinkSync", "fs.promises.unlinkSync",
        "fs/promises.unlinkSync", "fs.rename", "fs.promises.rename", "fs/promises.rename",
        "fs.renameSync", "fs.promises.renameSync", "fs/promises.renameSync", "fs.copyFile",
        "fs.promises.copyFile", "fs/promises.copyFile", "fs.copyFileSync",
        "fs.promises.copyFileSync", "fs/promises.copyFileSync", "fs.cp", "fs.promises.cp",
        "fs/promises.cp", "fs.cpSync", "fs.promises.cpSync", "fs/promises.cpSync", "fs.chmod",
        "fs.promises.chmod", "fs/promises.chmod", "fs.chmodSync", "fs.promises.chmodSync",
        "fs/promises.chmodSync", "fs.chown", "fs.promises.chown", "fs/promises.chown",
        "fs.chownSync", "fs.promises.chownSync", "fs/promises.chownSync", "fs.truncate",
        "fs.promises.truncate", "fs/promises.truncate", "fs.truncateSync",
        "fs.promises.truncateSync", "fs/promises.truncateSync", "fs.symlink",
        "fs.promises.symlink", "fs/promises.symlink", "fs.symlinkSync",
        "fs.promises.symlinkSync", "fs/promises.symlinkSync", "fs.link", "fs.promises.link",
        "fs/promises.link", "fs.linkSync", "fs.promises.linkSync", "fs/promises.linkSync",
        "fs.utimes", "fs.promises.utimes", "fs/promises.utimes", "fs.utimesSync",
        "fs.promises.utimesSync", "fs/promises.utimesSync", "fs.open", "fs.promises.open",
        "fs/promises.open", "fs.openSync", "fs.promises.openSync", "fs/promises.openSync",
        "fs.createWriteStream", "fs.promises.createWriteStream",
        "fs/promises.createWriteStream", "fs.write", "fs.promises.write", "fs/promises.write",
        "fs.writeSync", "fs.promises.writeSync", "fs/promises.writeSync", "Deno.writeTextFile",
        "Deno.writeFile", "Deno.mkdir", "Deno.remove", "Deno.rename", "Deno.copyFile",
        "Deno.makeTempFile", "Deno.makeTempDir", "Deno.open", "Deno.create", "Bun.write",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "net.connect", names: &[
        "http.request", "http.get", "https.request", "https.get", "http2.connect",
        "net.connect", "net.createConnection", "net.Socket", "tls.connect",
        "dgram.createSocket", "dns.lookup", "dns.resolve", "dns.promises.lookup",
        "dns.promises.resolve", "fetch", "XMLHttpRequest", "WebSocket", "EventSource", "axios",
        "axios.get", "axios.post", "axios.put", "axios.delete", "axios.patch", "axios.request",
        "axios.head", "node-fetch", "got", "got.get", "got.post", "got.put", "got.delete",
        "got.patch", "got.head", "undici.fetch", "undici.request", "Deno.connect",
        "Deno.connectTls",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "net.listen", names: &[
        "http.createServer", "https.createServer", "http2.createServer",
        "http2.createSecureServer", "net.createServer", "net.Server", "tls.createServer",
        "dgram.Socket", "Deno.listen", "Deno.listenTls", "Deno.serve", "Bun.serve", "express.listen", "express.Express.listen", "express.Application.listen",
        "Bun.listen",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "process.env", names: &[
        "process.env", "process.loadEnvFile", "Deno.env.get", "Deno.env.set",
        "Deno.env.toObject", "Deno.env.has", "Deno.env.delete", "Bun.env",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "code.eval", names: &[
        "eval", "Function", "vm.runInThisContext", "vm.runInNewContext", "vm.runInContext",
        "vm.Script", "vm.compileFunction",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "csharp", kind: "process.spawn", names: &[
        "System.Diagnostics.Process.Start", "System.Diagnostics.Process",
        "System.Diagnostics.ProcessStartInfo",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "csharp", kind: "fs.read", names: &[
        "System.IO.File.ReadAllText", "System.IO.File.ReadAllBytes",
        "System.IO.File.ReadAllLines", "System.IO.File.ReadLines",
        "System.IO.File.ReadAllTextAsync", "System.IO.File.ReadAllBytesAsync",
        "System.IO.File.ReadAllLinesAsync", "System.IO.File.OpenRead",
        "System.IO.File.OpenText", "System.IO.File.Open", "System.IO.File.Exists",
        "System.IO.File.GetAttributes", "System.IO.File.GetLastWriteTime",
        "System.IO.Directory.GetFiles", "System.IO.Directory.GetDirectories",
        "System.IO.Directory.GetFileSystemEntries", "System.IO.Directory.EnumerateFiles",
        "System.IO.Directory.EnumerateDirectories",
        "System.IO.Directory.EnumerateFileSystemEntries", "System.IO.Directory.Exists",
        "System.IO.FileStream", "System.IO.StreamReader", "System.IO.FileInfo",
        "System.IO.DirectoryInfo",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "csharp", kind: "fs.write", names: &[
        "System.IO.File.WriteAllText", "System.IO.File.WriteAllBytes",
        "System.IO.File.WriteAllLines", "System.IO.File.WriteAllTextAsync",
        "System.IO.File.WriteAllBytesAsync", "System.IO.File.WriteAllLinesAsync",
        "System.IO.File.AppendAllText", "System.IO.File.AppendAllLines",
        "System.IO.File.AppendAllTextAsync", "System.IO.File.AppendText",
        "System.IO.File.Create", "System.IO.File.CreateText", "System.IO.File.Open",
        "System.IO.File.OpenWrite", "System.IO.File.Delete", "System.IO.File.Copy",
        "System.IO.File.Move", "System.IO.File.Replace", "System.IO.File.SetAttributes",
        "System.IO.Directory.CreateDirectory", "System.IO.Directory.Delete",
        "System.IO.Directory.Move", "System.IO.FileStream", "System.IO.StreamWriter",
        "System.IO.FileInfo", "System.IO.DirectoryInfo", "System.IO.Path.GetTempFileName",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "csharp", kind: "net.connect", names: &[
        "System.Net.Http.HttpClient", "System.Net.WebClient", "System.Net.WebRequest.Create",
        "System.Net.WebRequest.CreateHttp", "System.Net.HttpWebRequest",
        "System.Net.Sockets.TcpClient", "System.Net.Sockets.UdpClient",
        "System.Net.Sockets.Socket", "System.Net.WebSockets.ClientWebSocket",
        "System.Net.Dns.GetHostEntry", "System.Net.Dns.GetHostAddresses",
        "System.Net.Dns.GetHostEntryAsync", "System.Net.Dns.GetHostAddressesAsync",
        "System.Net.Mail.SmtpClient", "System.Net.Http.HttpClient.GetAsync",
        "System.Net.Http.HttpClient.GetStringAsync",
        "System.Net.Http.HttpClient.GetByteArrayAsync",
        "System.Net.Http.HttpClient.GetStreamAsync", "System.Net.Http.HttpClient.PostAsync",
        "System.Net.Http.HttpClient.PutAsync", "System.Net.Http.HttpClient.DeleteAsync",
        "System.Net.Http.HttpClient.PatchAsync", "System.Net.Http.HttpClient.SendAsync",
        "System.Net.Http.HttpClient.Send", "System.Net.WebClient.DownloadString",
        "System.Net.WebClient.DownloadStringAsync", "System.Net.WebClient.DownloadData",
        "System.Net.WebClient.DownloadFile", "System.Net.WebClient.DownloadFileAsync",
        "System.Net.WebClient.UploadString", "System.Net.WebClient.UploadData",
        "System.Net.WebClient.UploadFile", "System.Net.WebClient.OpenRead",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "csharp", kind: "net.listen", names: &[
        "System.Net.Sockets.TcpListener", "System.Net.Sockets.Socket",
        "System.Net.HttpListener",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "csharp", kind: "process.env", names: &[
        "System.Environment.GetEnvironmentVariable",
        "System.Environment.GetEnvironmentVariables",
        "System.Environment.SetEnvironmentVariable",
        "System.Environment.ExpandEnvironmentVariables",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "csharp", kind: "code.eval", names: &[
        "System.Reflection.Assembly.Load", "System.Reflection.Assembly.LoadFrom",
        "System.Reflection.Assembly.LoadFile",
        "Microsoft.CodeAnalysis.CSharp.Scripting.CSharpScript.EvaluateAsync",
        "Microsoft.CodeAnalysis.CSharp.Scripting.CSharpScript.RunAsync",
        "Microsoft.CodeAnalysis.CSharp.Scripting.CSharpScript.Create",
        "System.CodeDom.Compiler.CodeDomProvider.CompileAssemblyFromSource",
    ] }
}

// Native interop and dynamic loading, ticket S3EC85S. A trailing `.*` names every member.
inventory::submit! {
    VocabEntry { lang: "csharp", kind: "ffi", names: &[
        "System.Runtime.InteropServices.DllImport",
        "System.Runtime.InteropServices.DllImportAttribute",
        "System.Runtime.InteropServices.LibraryImport",
        "System.Runtime.InteropServices.LibraryImportAttribute",
        "System.Runtime.InteropServices.NativeLibrary.*",
        "System.Runtime.InteropServices.Marshal.GetDelegateForFunctionPointer",
        "System.Runtime.InteropServices.Marshal.GetFunctionPointerForDelegate",
        "System.Runtime.InteropServices.Marshal.PrelinkAll",
        "System.Runtime.InteropServices.Marshal.Prelink",
    ] }
}

// Java, ticket 01M64VBRFWT0EKCG800ANRZDTE. Names are fully qualified; a trailing `.*` names every member.
inventory::submit! {
    VocabEntry { lang: "java", kind: "process.spawn", names: &[
        "java.lang.ProcessBuilder", "java.lang.ProcessBuilder.start",
        "java.lang.Runtime.exec", "java.lang.Runtime.getRuntime.exec",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "java", kind: "fs.read", names: &[
        "java.io.FileInputStream", "java.io.FileReader", "java.io.RandomAccessFile",
        "java.io.File.list", "java.io.File.listFiles", "java.io.File.exists",
        "java.io.File.length", "java.io.File.isFile", "java.io.File.isDirectory",
        "java.nio.file.Files.readAllBytes", "java.nio.file.Files.readString",
        "java.nio.file.Files.readAllLines", "java.nio.file.Files.lines",
        "java.nio.file.Files.newInputStream", "java.nio.file.Files.newBufferedReader",
        "java.nio.file.Files.list", "java.nio.file.Files.walk", "java.nio.file.Files.find",
        "java.nio.file.Files.exists", "java.nio.file.Files.size",
        "java.nio.file.Files.newDirectoryStream",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "java", kind: "fs.write", names: &[
        "java.io.FileOutputStream", "java.io.FileWriter", "java.io.File.delete",
        "java.io.File.createNewFile", "java.io.File.mkdir", "java.io.File.mkdirs",
        "java.io.File.renameTo", "java.io.File.createTempFile",
        "java.nio.file.Files.write", "java.nio.file.Files.writeString",
        "java.nio.file.Files.newOutputStream", "java.nio.file.Files.newBufferedWriter",
        "java.nio.file.Files.delete", "java.nio.file.Files.deleteIfExists",
        "java.nio.file.Files.copy", "java.nio.file.Files.move",
        "java.nio.file.Files.createFile", "java.nio.file.Files.createDirectory",
        "java.nio.file.Files.createDirectories", "java.nio.file.Files.createTempFile",
        "java.nio.file.Files.createTempDirectory", "java.nio.file.Files.createSymbolicLink",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "java", kind: "net.connect", names: &[
        "java.net.Socket", "java.net.URL.openConnection", "java.net.URL.openStream",
        "java.net.HttpURLConnection", "java.net.URLConnection",
        "java.net.http.HttpClient", "java.net.http.HttpClient.newHttpClient",
        "java.net.http.HttpClient.newBuilder", "java.net.http.HttpClient.send",
        "java.net.http.HttpClient.sendAsync", "java.net.InetAddress.getByName",
        "java.net.InetAddress.getAllByName", "java.nio.channels.SocketChannel",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "java", kind: "net.listen", names: &[
        "java.net.ServerSocket", "java.net.DatagramSocket",
        "java.nio.channels.ServerSocketChannel",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "java", kind: "process.env", names: &[
        "java.lang.System.getenv", "java.lang.System.getProperty",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "java", kind: "ffi", names: &[
        "java.lang.System.load", "java.lang.System.loadLibrary",
        "java.lang.Runtime.load", "java.lang.Runtime.loadLibrary",
        "java.lang.Runtime.getRuntime.load", "java.lang.Runtime.getRuntime.loadLibrary",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "java", kind: "code.eval", names: &[
        "java.lang.Class.forName", "java.lang.ClassLoader", "java.lang.ClassLoader.*",
        "java.lang.ClassLoader.loadClass", "java.lang.ClassLoader.defineClass",
        "java.lang.reflect.Method.invoke", "java.lang.reflect.Constructor.newInstance",
        "java.net.URLClassLoader",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "typescript", kind: "ffi", names: &[
        "process.dlopen", "process.binding", "process._linkedBinding", "Deno.dlopen",
        "Deno.UnsafeFnPointer", "Deno.UnsafePointer", "Bun.FFI.*", "bun:ffi.*",
    ] }
}

// Python process, network, environment, native-library, deserialization and archive entry points
// (ticket 01M6422ZVVSTEKVMY0PR269X33, audit cases p15 to p19 and p25). These union with the base
// Python vocabulary in grimble-model; a name is the import-resolved path, never spelled text.
inventory::submit! {
    VocabEntry { lang: "python", kind: "process.spawn", names: &[
        "os.execl", "os.execle", "os.execlp", "os.execlpe", "os.execve", "os.execvp",
        "os.execvpe", "os.spawnl", "os.spawnle", "os.spawnlp", "os.spawnlpe", "os.spawnv",
        concat!("os.spawn", "ve"), // split: the typos checker reads the word as a misspelling
        "os.spawnvp", "os.spawnvpe", "os.posix_spawn", "os.posix_spawnp",
        "os.startfile", "os.fork", "os.forkpty", "pty.spawn", "pty.fork",
        "asyncio.create_subprocess_exec", "asyncio.create_subprocess_shell",
        "asyncio.subprocess.create_subprocess_exec",
        "asyncio.subprocess.create_subprocess_shell", "subprocess.getoutput",
        "subprocess.getstatusoutput",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "net.connect", names: &[
        "http.client.HTTPConnection", "http.client.HTTPSConnection", "urllib3.PoolManager",
        "urllib3.ProxyManager", "urllib3.HTTPConnectionPool", "urllib3.HTTPSConnectionPool",
        "urllib3.connection_from_url", "urllib3.proxy_from_url", "urllib3.request",
        "urllib3.poolmanager.PoolManager", "urllib3.connectionpool.HTTPConnectionPool",
        "urllib3.connectionpool.HTTPSConnectionPool", "httpx.get", "httpx.post", "httpx.put",
        "httpx.patch", "httpx.delete", "httpx.head", "httpx.options", "httpx.request",
        "httpx.stream", "httpx.Client", "httpx.AsyncClient", "smtplib.SMTP", "smtplib.SMTP_SSL",
        "smtplib.LMTP", "ftplib.FTP", "ftplib.FTP_TLS", "asyncio.open_connection",
        "asyncio.open_unix_connection", "asyncio.streams.open_connection",
        "asyncio.streams.open_unix_connection", "urllib.request.urlretrieve",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "net.listen", names: &[
        "asyncio.start_server", "asyncio.start_unix_server", "asyncio.streams.start_server",
        "asyncio.streams.start_unix_server",
    ] }
}

// `os.environ` is read by subscript, iteration and method alike: a reference to it, or a call
// under it, is the use.
inventory::submit! {
    VocabEntry { lang: "python", kind: "process.env", names: &[
        "os.environ", "os.environb", "os.getenvb", "os.unsetenv",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "ffi", names: &[
        "ctypes.CDLL", "ctypes.PyDLL", "ctypes.WinDLL", "ctypes.OleDLL", "ctypes.LibraryLoader",
        "ctypes.cdll", "ctypes.windll", "ctypes.oledll", "ctypes.pydll", "ctypes.cdll.*",
        "ctypes.windll.*", "ctypes.oledll.*", "ctypes.pydll.*",
        "ctypes.util.find_library", "ctypes.util.find_msvcrt", "ctypes.pythonapi",
        "_ctypes.dlopen",
    ] }
}

// Loading a pickle runs the code its stream names, so every loader is a code.eval use.
inventory::submit! {
    VocabEntry { lang: "python", kind: "code.eval", names: &[
        "pickle.load", "pickle.loads", "pickle.Unpickler", "_pickle.load", "_pickle.loads",
        "_pickle.Unpickler", "marshal.load", "marshal.loads", "shelve.open", "dill.load",
        "dill.loads", "cloudpickle.load", "cloudpickle.loads",
    ] }
}

// Archive extraction writes the member paths the archive names (zip-slip), and opening reads.
inventory::submit! {
    VocabEntry { lang: "python", kind: "fs.write", names: &[
        "shutil.unpack_archive", "tarfile.TarFile.extractall", "tarfile.TarFile.extract",
        "zipfile.ZipFile.extractall", "zipfile.ZipFile.extract",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "fs.read", names: &[
        "tarfile.open", "tarfile.TarFile", "zipfile.ZipFile", "shutil.unpack_archive",
    ] }
}

// Go: os/exec, os, net, net/http and plugin members, named by `<import path>.<member>` as
// `go_uses` resolves them (ticket 01M64VBRCNYQ3WC895EYXR6GME, audit case g01).
// frob:ticket 01M64VBRCNYQ3WC895EYXR6GME
inventory::submit! {
    VocabEntry { lang: "go", kind: "process.spawn", names: &[
        "os/exec.Command", "os/exec.CommandContext", "os/exec.Cmd", "os.StartProcess",
        "os.FindProcess", "syscall.Exec", "syscall.ForkExec",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "go", kind: "fs.read", names: &[
        "os.Open", "os.OpenFile", "os.ReadFile", "os.ReadDir", "os.Stat", "os.Lstat",
        "os.Readlink", "os.DirFS", "io/ioutil.ReadFile", "io/ioutil.ReadDir",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "go", kind: "fs.write", names: &[
        "os.Create", "os.CreateTemp", "os.OpenFile", "os.WriteFile", "os.Remove",
        "os.RemoveAll", "os.Rename", "os.Mkdir", "os.MkdirAll", "os.MkdirTemp", "os.Chmod",
        "os.Chown", "os.Truncate", "os.Symlink", "os.Link", "io/ioutil.WriteFile",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "go", kind: "net.connect", names: &[
        "net.Dial", "net.DialTimeout", "net.DialTCP", "net.DialUDP", "net.DialIP",
        "net.DialUnix", "net.Dialer", "net.LookupHost", "net.LookupAddr", "net.LookupIP",
        "net.LookupCNAME", "net.LookupMX", "net.LookupTXT", "net.ResolveTCPAddr",
        "net/http.Get", "net/http.Post", "net/http.PostForm", "net/http.Head",
        "net/http.NewRequest", "net/http.NewRequestWithContext", "net/http.Client",
        "net/http.DefaultClient", "net/http.DefaultClient.Do", "net/http.DefaultClient.Get",
        "net/http.DefaultClient.Post", "net/http.DefaultClient.Head",
        "net/http.DefaultClient.PostForm", "net/http.DefaultTransport", "net/http.Transport",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "go", kind: "net.listen", names: &[
        "net.Listen", "net.ListenTCP", "net.ListenUDP", "net.ListenPacket", "net.ListenIP",
        "net.ListenUnix", "net.ListenConfig", "net/http.ListenAndServe",
        "net/http.ListenAndServeTLS", "net/http.Serve", "net/http.ServeTLS",
        "net/http.Server", "net/http.ServeFile", "net/http.FileServer",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "go", kind: "process.env", names: &[
        "os.Getenv", "os.LookupEnv", "os.Environ", "os.ExpandEnv", "os.Setenv",
        "os.Unsetenv", "os.Clearenv",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "go", kind: "ffi", names: &["plugin.Open", "plugin.Plugin", "plugin.Symbol"] }
}
