using System;

namespace Acme.App
{
    /// <summary>Platform specific behaviour behind preprocessor branches.</summary>
    public static class Platform
    {
        /// <summary>The platform label.</summary>
        public static string Label()
        {
#if WINDOWS
            return "windows";
#elif LINUX
            return "linux";
#else
            return Environment.OSVersion.Platform.ToString();
#endif
        }
    }
}
