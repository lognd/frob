// frob:ticket T-4536
// Regression fixture: `using static System.Console;` and `using
// System.IO;` in the same file -- the `using static` fallback must
// resolve only a BARE call target (`WriteLine(...)`), never hijack a
// member-access base like `File.WriteAllText(...)`.
using System.IO;
using static System.Console;

class CombinedStaticAndNamespace
{
    static void Run()
    {
        File.WriteAllText("out.txt", "payload");
        WriteLine("done");
    }
}
