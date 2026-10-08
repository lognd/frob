import React from "react";

export function Button({ children, extraClass }: Props) {
  return (
    <button
      style={{
        background: "#282828",
        width: 44,
        zIndex: 5,
        color: computeColor(),
        label: `prefix-${extraClass}`,
      }}
      className="bg-[#282828] p-[13px] hover:bg-red-500 [&>x]:text-sm"
    >
      <span
        style={dynamicStyles}
        className={`extra ${extraClass}`}
      >
        {children}
      </span>
    </button>
  );
}
