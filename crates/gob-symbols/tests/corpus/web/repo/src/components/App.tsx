import { fetchUser, label } from "@api/client";
import { Button } from "./Button";

/** The root component. */
export function App() {
  const user = fetchUser(1);
  return (
    <div id="app">
      <Button label={label(user)} />
    </div>
  );
}
