// frob:ticket T-4511
// Taxonomy row: `Activator.CreateInstance(typeName)` -- resolves a type
// from a runtime string name, maps to eval.
using System;

class DotnetBclActivatorCreateInstanceEval
{
    static void Run(string typeName)
    {
        Activator.CreateInstance(typeName);
    }
}
