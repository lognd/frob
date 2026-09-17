using System.Collections;
using UnityEngine;

namespace Frob.Sample.Unity
{
    public class Spawner : MonoBehaviour
    {
        // No visible caller in this file -- started elsewhere via
        // StartCoroutine(SpawnLoop()), which this single-file walker
        // cannot trace.
        private IEnumerator SpawnLoop()
        {
            yield return null;
        }

        // A plain private method returning void, not IEnumerator and not
        // a lifecycle name -- must stay non-public (negative case).
        private void NotACoroutine() {}
    }
}
