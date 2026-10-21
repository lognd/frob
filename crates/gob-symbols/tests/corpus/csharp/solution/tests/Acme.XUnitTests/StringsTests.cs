using Acme.Lib;
using Xunit;

namespace Acme.XUnitTests
{
    public class StringsTests
    {
        [Fact]
        public void Shout_AppendsBang()
        {
            Assert.Equal("HI!", "hi".Shout());
        }

        [Theory]
        [InlineData("x")]
        [InlineData("y")]
        public void Shout_UpperCases(string text)
        {
            Assert.Equal(text.ToUpperInvariant() + "!", text.Shout());
        }
    }
}
