public class WithConditional
{
    public int Pick(
#if DEBUG
        int extra,
#endif
        int value)
    {
        return value;
    }
}
