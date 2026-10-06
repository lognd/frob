import "../styles/app.css";

/** A push button. */
export function Button(props: { label: string }) {
  return (
    <button className="btn" style={{ color: "red" }}>
      {props.label}
    </button>
  );
}
