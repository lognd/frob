<!-- mdtest: rule=UNITY004 -->
# UNITY004

## A violating case fires

```csharp expect=fire file=Assets/Hero.cs
public class Hero {
    private int plain; // error: UNITY004
}
```

## An assigned field is clean

```csharp expect=clean file=Assets/Hero.cs
public class Hero {
    private int plain;
    void Reset() { plain = 1; }
}
```
