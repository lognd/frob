import { useEffect, useRef } from "react";

export default function GoodPage() {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    document.title = "Home";
    heading.current?.focus();
  }, []);
  return <h1 ref={heading} tabIndex={-1}>Home</h1>;
}
