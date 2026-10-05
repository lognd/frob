namespace Hullbreach.Game
{
    [Obsolete("use Hull")]
    public partial class Ship : Component
    {
        public void Damage(int amount)
        {
            Hull -= amount;
        }
    }
}
