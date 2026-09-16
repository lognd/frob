// frob:ticket T-4536
// Taxonomy row: `var client = new System.Net.Http.HttpClient();
// client.GetAsync(url);` -- a `var` local's TYPE, bound from its `new`
// expression, carries into a later instance-method call site.
class VarLocalHttpClient
{
    static void Run()
    {
        var client = new System.Net.Http.HttpClient();
        client.GetAsync("https://example.invalid/");
    }
}
