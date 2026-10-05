using System;

Console.WriteLine("top-level statements are not modelled");

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

    public int Stable()
    {
        return 3;
    }
}
