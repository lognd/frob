public class WithConditional
{
    public int Pick()
    {
#if DEBUG
        return 1;
#else
        return 2;
#endif
    }
}
