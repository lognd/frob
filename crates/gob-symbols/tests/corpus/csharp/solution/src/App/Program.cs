using System;

namespace Acme.App
{
    /// <summary>Entry point.</summary>
    public static class Program
    {
        /// <summary>Run the app.</summary>
        public static int Main()
        {
            var widget = new Widget();
            Console.WriteLine(widget.Describe());
            Console.WriteLine(Platform.Label());
            return 0;
        }
    }
}
