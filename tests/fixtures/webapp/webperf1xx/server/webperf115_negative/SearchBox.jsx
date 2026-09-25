import { debounce } from "lodash";

export function SearchBox({ onSearch }) {
  const debounced = debounce(onSearch, 300);
  return <input onChange={(e) => debounced(e.target.value)} />;
}
