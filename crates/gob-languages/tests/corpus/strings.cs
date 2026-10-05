#region Player's data "quoted
using System;

namespace Game
{
    /// <summary>TODO real xml doc</summary>
    public class Player
    {
        // real one
        public string A = "// no /* no";
        public string B = @"verbatim // no
""still // no"" /* no */";
        public string C = $"interp // no {Name("/* no")} {{ // no }}";
        public string D = $@"both // no {1 + 2} ""x"" // no";
        public string E = """
            raw // no /* no */ "quoted" ""
            """;
        public string F = $$"""raw {{Name("// no")}} { // no """;
        public char G = '"'; // real two
        public char H = '\'';
#if DEBUG // real three
        public int I = 1; /* real four */
#endif
    }
}
