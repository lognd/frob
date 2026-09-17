using NUnit.Framework;

namespace Frob.Fixtures.Csharp
{
    public class SampleNunitTests
    {
        [SetUp]
        public void Setup()
        {
        }

        [TearDown]
        public void Teardown()
        {
        }

        [Test]
        public void AddsTwoNumbers()
        {
            Assert.AreEqual(4, 2 + 2);
        }

        [TestCase(1, 2)]
        [TestCase(3, 4)]
        public void AddsPair(int a, int b)
        {
            Assert.That(a + b, Is.GreaterThan(0));
        }
    }
}
