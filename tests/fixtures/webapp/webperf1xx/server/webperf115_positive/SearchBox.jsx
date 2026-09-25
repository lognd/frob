export function SearchBox({ onSearch }) {
  return <input onChange={(e) => onSearch(e.target.value)} />;
}
