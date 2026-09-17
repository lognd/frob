// frob:ticket T-4511
// Taxonomy row: `new StreamReader(...)` -- System.IO StreamReader maps
// to fs-read.
using System.IO;

class DotnetBclStreamReaderFsRead
{
    static void Run(string path)
    {
        var reader = new StreamReader(path);
        reader.ReadToEnd();
    }
}
