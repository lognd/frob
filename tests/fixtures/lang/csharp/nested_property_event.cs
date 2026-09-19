// frob:ticket T-4519
// Static fixture for T-4519's docs/xref csharp proof coverage: a
// namespaced class with a nested type, a property, a const field, and
// an event -- exercising member kinds `sample.cs` (T-3232) does not
// (that fixture has a property/const/method but no nested class or
// event). The `Changed` event is deliberately included even though
// nothing in frob.lang extracts it as a RawSymbol yet (`_walk_csharp.py`
// has no `event_declaration` case) -- see the event-lookup test's own
// comment for why that gap is out of this ticket's scope.
using System;

namespace Frob.Sample.Nested
{
    /// <summary>Outer container exercising nested-type and property xref lookups.</summary>
    public class Container
    {
        /// <summary>A nested type; xref must resolve it by its own bare name.</summary>
        public class Inner
        {
            public void Ping()
            {
            }
        }

        /// <summary>Running total; a property, not a plain field.</summary>
        public int Total { get; set; }

        public const int MaxTotal = 100;

        public event EventHandler Changed;

        public void Bump()
        {
            Total = Total + 1;
        }
    }
}
