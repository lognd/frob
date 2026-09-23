// Positive control: Prisma tagged-template $queryRaw with a literal SQL
// string (no interpolation) -- extracted verbatim, no WEBSEC107 finding.
//
// frob:ticket T-5334

export async function countUsers(prisma: any): Promise<number> {
  return prisma.$queryRaw`SELECT count(*) FROM users`;
}
