// frob:ticket T-4511
// Taxonomy row: `Registry.SetValue(...)` -- Microsoft.Win32.Registry
// maps to fs-write.
using Microsoft.Win32;

class DotnetBclRegistryFsWrite
{
    static void Run(string key, string name, string value)
    {
        Registry.SetValue(key, name, value);
    }
}
