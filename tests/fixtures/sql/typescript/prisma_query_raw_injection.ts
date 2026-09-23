// Negative control: Prisma tagged-template $queryRaw with an interpolated
// table name -- WEBSEC107 (CWE-89 SQL injection sink).
//
// frob:ticket T-5334

export async function fetchFromTable(prisma: any, tableName: string): Promise<any> {
  return prisma.$queryRaw`SELECT * FROM ${tableName}`;
}
