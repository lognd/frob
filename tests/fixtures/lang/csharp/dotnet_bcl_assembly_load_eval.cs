// frob:ticket T-4511
// Taxonomy row: `Assembly.Load(...)` -- System.Reflection dynamic
// assembly load maps to eval, distinct from a plain method call finding.
using System.Reflection;

class DotnetBclAssemblyLoadEval
{
    static void Run(byte[] raw)
    {
        Assembly.Load(raw);
    }
}
