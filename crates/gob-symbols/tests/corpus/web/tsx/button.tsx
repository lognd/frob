export function Button(props: { label: string }) {
  return (
    <button className="btn" style={{ color: "red" }}>
      {props.label}
    </button>
  );
}
