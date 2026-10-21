using Acme.App;
using NUnit.Framework;

namespace Acme.NUnitTests
{
    [TestFixture]
    public class WidgetTests
    {
        [Test]
        public void Describe_ShoutsTheName()
        {
            var widget = new Widget();
            Assert.AreEqual("WIDGET!", widget.Describe());
        }

        [TestCase("a")]
        [TestCase("b")]
        public void Name_RoundTrips(string name)
        {
            var widget = new Widget { Name = name };
            Assert.AreEqual(name, widget.Name);
        }
    }
}
