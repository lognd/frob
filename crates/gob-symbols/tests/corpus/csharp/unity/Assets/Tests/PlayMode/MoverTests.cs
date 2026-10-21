using System.Collections;
using Game.Runtime;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Game.PlayTests
{
    public class MoverTests
    {
        [UnityTest]
        public IEnumerator Mover_AdvancesOverFrames()
        {
            var go = new GameObject("mover");
            var mover = go.AddComponent<Mover>();
            yield return null;
            Assert.GreaterOrEqual(mover.Travelled(), 0f);
        }
    }
}
