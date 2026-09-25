from supabase import create_client

client = create_client("https://project.supabase.co", ANON_KEY)
client.postgrest.auth(service_role=True)
