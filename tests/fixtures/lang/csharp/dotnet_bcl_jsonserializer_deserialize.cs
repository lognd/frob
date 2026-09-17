// frob:ticket T-4511
// Taxonomy row: `JsonSerializer.Deserialize(...)` -- System.Text.Json
// maps to deserialize.
using System.Text.Json;

class DotnetBclJsonSerializerDeserialize
{
    static object Run(string json)
    {
        return JsonSerializer.Deserialize<object>(json);
    }
}
