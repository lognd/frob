// frob:ticket T-4511
// Taxonomy row: `new SqlCommand(...)` -- System.Data SqlCommand maps to
// sql.
using System.Data.SqlClient;

class DotnetBclSqlCommandSql
{
    static void Run(string commandText, SqlConnection conn)
    {
        var command = new SqlCommand(commandText, conn);
        command.ExecuteNonQuery();
    }
}
