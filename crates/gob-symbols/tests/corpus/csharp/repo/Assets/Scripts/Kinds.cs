using System;

namespace Hullbreach.Core;

public record BlockKey(int X, int Y);

public interface IShip
{
    int Hull { get; }
    void Repair();
}

public enum BlockType : byte
{
    Core,
    Hull = 2,
#if UNITY_EDITOR
    Debug
#endif
}

public delegate void Hit(int amount);

public class Grid
{
    public const int Size = 8;

    public int this[int i] => i;

    public static Grid operator +(Grid a, Grid b) => a;

    public static implicit operator int(Grid g) => 0;

    ~Grid() { }

    static Grid() { }

    public Grid() { }

    void IDisposable.Dispose() { }

    public int Total()
    {
        int Sum(int a, int b)
        {
            return a + b;
        }

        return Sum(1, 2);
    }
}
