// frob:ticket T-4511
// Taxonomy row: `Dns.GetHostAddresses(...)` -- System.Net.Sockets.Dns
// maps to net.
using System.Net.Sockets;

class DotnetBclDnsNet
{
    static void Run(string host)
    {
        Dns.GetHostAddresses(host);
    }
}
