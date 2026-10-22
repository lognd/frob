export async function GET() {
  return new Response("list");
}
export async function POST() {
  return new Response("create");
}
export async function remove() {
  return new Response("gone");
}
