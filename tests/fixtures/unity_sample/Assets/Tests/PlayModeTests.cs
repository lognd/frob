// T-4509 (Unity capstone fixture): one NUnit [Test] and one Unity Test
// Framework [UnityTest] -- proves T-4516/T-4517's collector picks up
// both attribute families from a real Unity test assembly (Tests.asmdef,
// defineConstraints=["UNITY_INCLUDE_TESTS"]).
using System.Collections;
using NUnit.Framework;
using UnityEngine.TestTools;

namespace Game.Tests
{
    public class PlayModeTests
    {
        [Test]
        public void AddScores_ReturnsSum()
        {
            Assert.AreEqual(5, 2 + 3);
        }

        [UnityTest]
        public IEnumerator Player_Respawns_AfterOneFrame()
        {
            yield return null;
            Assert.Pass();
        }
    }
}
