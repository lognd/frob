import { cva } from "class-variance-authority";
import { twMerge, twJoin } from "tailwind-merge";
import clsx from "clsx";

export const Cases = ({ open, cond, c, x, extraCls, fn }: Props) => (
  <section>
    <div style={{ backgroundColor: "#282828", zIndex: 5, width: 44 }} />
    <div style={{ margin: "4px 13px", padding: -4, opacity: 0.5 }} />
    <div style={{ ...base, color: computeColor(), [dynamicKey]: "red", label: `${prefix}-x` }} />
    <div
      style={{
        background: "#fff",
        width: 10,
        boxShadow: `0 1px ${blur}px red`,
        border: '1px solid #ccc',
      }}
    />
    <div className="bg-[#282828] p-[13px] hover:bg-red-500 [&>x]:text-sm" />
    <div className={`bg-red-500 p-4`} />
    <div className={`bg-red-500 ${extra}`} />
    <div className={`a z-footer ${c}`} />
    <div className={`z-${x}`} />
    <div className={clsx("p-4 flex", extraCls)} />
    <div className={open ? "bg-red-500" : "bg-blue-500"} />
    <div className={`a ${fn({ x: 1, y: { z: 2 } })} b`} />
    <div className="hover:md:flex bg-red-500" />
    <div
      className={cva("base-class", {
        variants: { intent: { primary: "text-blue-500", danger: "text-red-500" } },
      })({ intent: "primary" })}
    />
    <div className={twMerge("p-4 flex", twJoin("gap-2", cond && "hidden"))} />
    <div className={`static-token ${fullyDynamicExpr()}`} />
    <div class="legacy-class mt-[3px]" />
    <div className={x} />
  </section>
);
