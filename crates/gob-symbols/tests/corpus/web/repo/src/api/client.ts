export interface User {
  id: number;
  name: string;
}

/** Fetches one user by id. */
export function fetchUser(id: number): User {
  return { id, name: `user-${id}` };
}

/** Formats a user for display. */
export function label(user: User): string {
  return user.name;
}
