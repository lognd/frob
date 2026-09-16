// frob:ticket T-4536
// Taxonomy row: `using static System.Console; WriteLine(...)` -- a bare
// call reachable only through a `using static` directive.
using static System.Console;

class StaticUsingConsole
{
    static void Run()
    {
        WriteLine("hi");
    }
}
