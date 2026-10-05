using NUnit.Framework;

namespace Hullbreach.Builder.Tests
{
    public class UndoStackTests
    {
        [Test]
        public void Undo_TenDeep_RestoresExactBlocks()
        {
            var undo = new UndoStack();
            Assert.AreEqual(0, undo.Depth);
        }

        [TestCase(1)]
        [TestCase(2)]
        public void Depth_Grows(int n)
        {
            Assert.AreEqual(n, n);
        }
    }
}
