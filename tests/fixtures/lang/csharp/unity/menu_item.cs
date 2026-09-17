using UnityEditor;

namespace Frob.Sample.Unity.Editor
{
    public static class Tools
    {
        // Invoked from the Unity Editor's own menu, not from any in-repo
        // call site.
        [MenuItem("Frob/Do Thing")]
        private static void DoThing() {}
    }

    [InitializeOnLoad]
    internal static class AutoInit
    {
        static AutoInit() {}
    }
}
