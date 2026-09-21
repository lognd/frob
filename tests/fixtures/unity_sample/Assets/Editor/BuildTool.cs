// T-4509 (Unity capstone fixture): an Editor-only script calling a
// UnityEditor-only API (T-4514's map) -- deliberately NOT covered by its
// own asmdef (the ticket's two-asmdef acceptance criterion names only
// Runtime.asmdef and Tests.asmdef), so this file falls into Unity's
// implicit default-assembly node, and its UnityEditor.* usage is
// fully-qualified so the capability scan's disclosed editor-api-in-
// runtime fallback (src/frob/vet/_capability_registry/_unity_api.py's
// own docstring) has real text to match against.
namespace Game.Editor
{
    public static class BuildTool
    {
        [UnityEditor.MenuItem("Game/Bake Level Asset")]
        public static void BakeLevelAsset()
        {
            var asset = UnityEngine.ScriptableObject.CreateInstance<UnityEngine.ScriptableObject>();
            UnityEditor.AssetDatabase.CreateAsset(asset, "Assets/Generated/Baked.asset");
        }
    }
}
