<!-- mdtest: rule=UNITY302 -->
# UNITY302 physics-force-outside-fixed-update

A Rigidbody force or move applied from Update or LateUpdate instead of FixedUpdate.

## What it does

Fires in a Unity C# file (one that names `UnityEngine` or a `MonoBehaviour`) for `AddForce` and its kin (`AddTorque`, `AddRelativeForce`, `AddForceAtPosition`, `AddExplosionForce`) and `MovePosition` or `MoveRotation` on a receiver known to be a body, made in `Update` or `LateUpdate` or in a method of the same class they call. It also fires on `transform.position`, `transform.rotation`, `Translate` and `Rotate` in a class that has Rigidbody evidence and does not make the body kinematic. A force-style call on a receiver the scan cannot resolve is Unresolved. A one-shot `ForceMode.Impulse` or `VelocityChange` under an edge-triggered input check (`GetKeyDown`, `wasPressedThisFrame`) runs once per press and is clean, and so is anything in `FixedUpdate`. A coroutine helper is not followed. A plain .NET class that names no Unity type is not examined, and the rule needs no project settings. The rule is Warn.

## Why it matters

Physics steps on a fixed timestep, so a force applied once per rendered frame scales with the frame rate: the same input pushes a body harder on a fast machine than on a slow one.

## Remedy

Move the call into `FixedUpdate`, or read the input in `Update` into a field and apply the force from `FixedUpdate`.

## Examples

### Fires case 1

```csharp expect=fire file=Assets/Scripts/Pusher.cs
using UnityEngine;

public class Pusher : MonoBehaviour
{
    Rigidbody body;

    void Awake()
    {
        body = GetComponent<Rigidbody>();
    }

    void Update()
    {
        body.AddForce(Vector3.forward);
    }
}
```

### Clean case 2

```csharp expect=clean file=Assets/Scripts/Pusher.cs
using UnityEngine;

public class Pusher : MonoBehaviour
{
    Rigidbody body;

    void Awake()
    {
        body = GetComponent<Rigidbody>();
    }

    void FixedUpdate()
    {
        body.AddForce(Vector3.forward);
    }
}
```

### Clean case 3

```csharp expect=clean file=Assets/Scripts/Jumper.cs
using UnityEngine;

public class Jumper : MonoBehaviour
{
    Rigidbody body;

    void Awake()
    {
        body = GetComponent<Rigidbody>();
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Space))
        {
            body.AddForce(Vector3.up, ForceMode.Impulse);
        }
    }
}
```
