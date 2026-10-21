<!-- mdtest: rule=UNITY001 -->
# UNITY001

## A violating case fires

```csharp expect=fire file=Assets/Hero.cs
public class Hero { } // warn: UNITY001
```

## A conforming case is clean

```csharp expect=clean file=Assets/.hidden.cs
public class Hidden { }
```
