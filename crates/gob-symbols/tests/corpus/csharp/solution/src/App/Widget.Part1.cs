namespace Acme.App
{
    /// <summary>A widget split over two files.</summary>
    public partial class Widget
    {
        /// <summary>The widget name.</summary>
        public string Name { get; set; } = "widget";

        /// <summary>Describe the widget.</summary>
        public string Describe()
        {
            return Decorate(Name);
        }
    }
}
