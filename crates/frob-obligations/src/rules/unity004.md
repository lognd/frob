<!-- mdtest: rule=UNITY004 -->
# UNITY004 field-never-written

A C# field is declared but no code assigns it and the engine does not write it either.

## What it does

With the opt-in `unity` pack enabled, every C# field (or auto-property with `[field: ...]` attributes) that has no initializer and whose name is never assigned in the repository's `.cs` files is reported. A `[SerializeField]` field, or a public instance field of a `MonoBehaviour` or `ScriptableObject` type, is written by the engine (scenes, prefabs, the Inspector) and is not reported; `[NonSerialized]`, static, const and readonly members still are. The assignment scan is lexical and name based.

## Why it matters

A field nothing assigns always holds its default value, which is usually a forgotten wiring rather than intent.

## Remedy

Assign the field, give it an initializer, or remove it. Mark it `[SerializeField]` if the Inspector is meant to set it.

## Examples

### A violating case fires

```csharp expect=fire file=Assets/Hero.cs
public class Hero {
    private int plain; // error: UNITY004
}
```

### An assigned field is clean

```csharp expect=clean file=Assets/Hero.cs
public class Hero {
    private int plain;
    void Reset() { plain = 1; }
}
```
