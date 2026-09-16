// frob:ticket T-4536
// Taxonomy row: `using IO = System.IO; IO.File.WriteAllText(...)` -- a
// namespace ALIAS the raw-text needle scan follows only because the
// resolver substitutes the alias, not because of any needle-text
// coincidence.
using IO = System.IO;

class AliasUsingFsWrite
{
    static void Run()
    {
        IO.File.WriteAllText("out.txt", "payload");
    }
}
