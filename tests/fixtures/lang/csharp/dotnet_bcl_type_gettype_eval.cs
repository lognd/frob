// frob:ticket T-4511
// Taxonomy row: `Type.GetType(typeName)` -- resolves a Type from a
// runtime string name, maps to eval.
using System;

class DotnetBclTypeGetTypeEval
{
    static void Run(string typeName)
    {
        Type.GetType(typeName);
    }
}
