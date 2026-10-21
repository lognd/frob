namespace Acme.Lib
{
    /// <summary>Extension helpers over strings.</summary>
    public static class StringExtensions
    {
        /// <summary>Shout the text.</summary>
        public static string Shout(this string text)
        {
            return text.ToUpperInvariant() + "!";
        }
    }
}
