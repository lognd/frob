// Static fixture for T-4507 -- one comment form per case, exercising the
// C# comment-DSL directive path (`//`, `///` XML-doc, and `/* */`) the
// same way the python `#`-comment path is exercised.
namespace Frob.Fixtures
{
    /// <summary>
    /// frob:waive DIRTEST001 reason="fixture class for T-4507 directive parity tests"
    /// </summary>
    public class Widget
    {
        // frob:doc docs/modules/lang.md#per-language-walker-notes
        public void SlashDoc()
        {
        }

        /// frob:doc docs/modules/lang.md#per-language-walker-notes
        public void XmlDocDoc()
        {
        }

        /* frob:doc docs/modules/lang.md#per-language-walker-notes */
        public void BlockDoc()
        {
        }

        /// frob:todo T-4507 free-text note about deferred cleanup here
        public void XmlDocTodo()
        {
        }

        // frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_tests_directive_binds  # noqa: E501
        public void SlashTests()
        {
        }

        // frob:ticket T-4507
        // frob:doc docs/modules/lang.md#per-language-walker-notes
        // Multi-line directive run: two directive comment lines stacked
        // directly above the same symbol, no blank line between them.
        public void MultiLineRun()
        {
        }
    }
}
