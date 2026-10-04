const computedColor = getColor();
export function Card() {
  return <div style={{ background: "#000", padding: 44, color: computedColor, borderRadius: `${radius}px` }} />;
}
