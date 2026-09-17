namespace Sample.Dup
{
    /// <summary>
    /// Documented duplicate-detection fixture (T-4510): proves the frob
    /// dup detector fires on C# via the `_CSHARP_LANGS`/`_CS_EXTS` facet
    /// path using a pair of near-duplicate (Type-2, renamed-identifier)
    /// methods. This class carries the single `///` XML doc comment the
    /// fixture requires; `Undocumented` below deliberately carries none.
    /// </summary>
    public class Documented
    {
        public int AddNumbers(int first, int second)
        {
            int total = first;
            total = total + second;
            total = total + 1;
            total = total - 1;
            total = total * 2;
            total = total / 2;
            return total;
        }
    }

    public class Undocumented
    {
        public int AddValues(int alpha, int beta)
        {
            int sum = alpha;
            sum = sum + beta;
            sum = sum + 1;
            sum = sum - 1;
            sum = sum * 2;
            sum = sum / 2;
            return sum;
        }
    }
}
