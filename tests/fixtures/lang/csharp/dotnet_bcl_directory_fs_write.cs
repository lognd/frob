// frob:ticket T-4511
// Taxonomy row: Directory.CreateDirectory at an attacker-influenceable
// path -- System.IO Directory family maps to fs-write.
using System.IO;

class DotnetBclDirectoryFsWrite
{
    static void Run(string path)
    {
        Directory.CreateDirectory(path);
    }
}
