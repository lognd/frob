// frob:ticket T-4536
// Taxonomy row: no dangerous APIs at all -- the wired resolver must add
// zero findings of its own (no false positives).
using System;

class NoDangerousApis
{
    static int Add(int a, int b)
    {
        return a + b;
    }

    static void Run()
    {
        Console.WriteLine(Add(2, 3));
    }
}
