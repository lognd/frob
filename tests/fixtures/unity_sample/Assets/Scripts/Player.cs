// T-4509 (Unity capstone fixture): a MonoBehaviour exercising two of
// T-4514's dead-code-exemption roots (a lifecycle method, a coroutine)
// plus three .NET BCL capability findings (T-4511's map) that a clean
// runtime script would genuinely make -- net, fs-write, exec.
using System.Collections;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using UnityEngine;

namespace Game.Runtime
{
    public class Player : MonoBehaviour
    {
        // Unity lifecycle method (T-4514): invoked by Unity's own
        // component-message dispatch every frame, with no visible
        // in-repo call site -- must NOT be flagged dead code even though
        // its own access modifier is the C# default (private, no
        // explicit `private` keyword written).
        void Update()
        {
            transform.Translate(Vector3.forward * Time.deltaTime);
        }

        void Start()
        {
            StartCoroutine(RespawnRoutine());
        }

        // Coroutine (T-4514): reachable the moment StartCoroutine(...)
        // above names it -- must NOT be flagged dead code.
        IEnumerator RespawnRoutine()
        {
            yield return null;
            transform.position = Vector3.zero;
        }

        // .NET BCL capability calls (T-4511's map): net (fetch_url via
        // HttpClient.GetAsync), fs-write (File.WriteAllText), exec
        // (Process.Start) -- a genuine, clean use of each, no attacker-
        // influenced input, exercised here purely to prove the capability
        // scan fires on first-party Unity runtime code the same way it
        // already does on a plain C# console-app fixture.
        public void ReportMatchResult(string telemetryUrl, string logPath)
        {
            var client = new HttpClient();
            client.GetAsync(telemetryUrl);

            File.WriteAllText(logPath, "match reported");

            Process.Start("git", "rev-parse HEAD");
        }
    }
}
