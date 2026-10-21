using Acme.Lib;

namespace Acme.App
{
    public partial class Widget
    {
        private string Decorate(string text)
        {
            return text.Shout();
        }
    }
}
