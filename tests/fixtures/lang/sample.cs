using System;

namespace Frob.Sample
{
    /// <summary>Adds two numbers.</summary>
    public class Widget
    {
        public int Count { get; set; }

        private int hidden;

        public const int MaxWidgets = 10;

        /// <summary>Renders the widget.</summary>
        public string Render(string label)
        {
            // sum them
            return Add(label);
        }

        private string Add(string label)
        {
            return label;
        }
    }

    internal interface IThing
    {
        void Do();
    }

    public enum Color
    {
        Red,
        Green,
        Blue,
    }
}
