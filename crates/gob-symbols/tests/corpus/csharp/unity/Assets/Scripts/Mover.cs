using UnityEngine;

namespace Game.Runtime
{
    /// <summary>Moves its object forward every frame.</summary>
    public class Mover : MonoBehaviour
    {
        [SerializeField] private float speed = 2f;

        private Vector3 start;

        private void Awake()
        {
            start = transform.position;
        }

        private void Update()
        {
            transform.Translate(Vector3.forward * speed * Time.deltaTime);
        }

        /// <summary>Distance travelled from the start.</summary>
        public float Travelled()
        {
            return Vector3.Distance(start, transform.position);
        }
    }
}
