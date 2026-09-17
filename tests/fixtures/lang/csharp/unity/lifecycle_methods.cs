using UnityEngine;

namespace Frob.Sample.Unity
{
    public class Player : MonoBehaviour
    {
        // Private, no visible caller anywhere -- Unity's component
        // message system invokes this by name every frame.
        private void Update()
        {
        }

        private void Awake() {}

        void OnTriggerEnter2D(Collider2D other) {}

        // A genuinely private helper with no lifecycle name and no
        // caller -- must stay non-public (T-4514 negative case).
        private void DoNothing() {}
    }
}
