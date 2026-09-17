// frob:ticket T-4511
// Taxonomy row: `new StreamWriter(...)` -- System.IO StreamWriter maps
// to fs-write.
using System.IO;

class DotnetBclStreamWriterFsWrite
{
    static void Run(string path)
    {
        var writer = new StreamWriter(path);
        writer.WriteLine("payload");
    }
}
