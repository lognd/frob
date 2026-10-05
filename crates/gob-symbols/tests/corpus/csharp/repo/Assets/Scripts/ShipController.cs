using System;
using UnityEngine;

namespace Hullbreach.Game
{
    // A plain struct because Phase A only needs "a ship exists to fly".
    [Serializable]
    public struct AuthoredBlock
    {
        public int x;
        public int y;
        public byte typeId, modifiers;

        public AuthoredBlock(int x, int y, byte typeId, byte modifiers = 0)
        {
            this.x = x;
            this.y = y;
            this.typeId = typeId;
            this.modifiers = modifiers;
        }
    }

    // The MonoBehaviour adapter. Lifecycle and Inspector wiring ONLY.
    [DefaultExecutionOrder(-100)]
    [RequireComponent(typeof(Rigidbody2D))]
    public sealed class ShipController : MonoBehaviour
    {
        [SerializeField] Rigidbody2D body;

        [Header("Tuning")]
        [Tooltip("Force each forward thruster applies at full throttle.")]
        [SerializeField] float thrustPerBlock = 10f;

        [field: SerializeField] public int Lives { get; private set; }

        public event Action Destroyed;

        void Awake()
        {
            body = GetComponent<Rigidbody2D>();
        }

        public float Thrust(int blocks)
        {
            float Scale(float v) => v * thrustPerBlock;
            return Scale(blocks);
        }
    }
}
