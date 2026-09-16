// frob:ticket T-4536
// Taxonomy row: `using System.IO; File.WriteAllText(...)` -- a plain
// namespace using bringing an unqualified dangerous type into scope.
using System.IO;

class PlainUsingFsWrite
{
    static void Run()
    {
        File.WriteAllText("out.txt", "payload");
    }
}
