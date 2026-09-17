using System.Collections;
using NUnit.Framework;
using UnityEngine.TestTools;

namespace Frob.Fixtures.Csharp
{
    public class SampleUnityTests
    {
        [UnityTest]
        public IEnumerator SpawnsPlayerNextFrame()
        {
            yield return null;
        }
    }
}
