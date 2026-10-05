using UnityEditor;

namespace Hullbreach.Editor
{
#if UNITY_EDITOR
    public static class HudPrefabBuilder
    {
        public const string HullWarningBannerPrefabPath = "Assets/Prefabs/UI/HullWarningBanner.prefab";

        [MenuItem("Hullbreach/UI/Rebuild default HUD prefabs")]
        public static void RebuildDefaultHudPrefabsMenuItem() => Run(force: false);

        public static void Build() => Run(force: false);

        static void Run(bool force)
        {
        }
    }
#else
    public static class HudPrefabBuilder
    {
        public static void Build()
        {
        }
    }
#endif
}
