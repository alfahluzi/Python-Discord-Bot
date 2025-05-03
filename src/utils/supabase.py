import os

from supabase import Client, create_client
from supabase.client import ClientOptions

from utils.logger import Logger

logger = Logger(__file__)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase_client: Client = create_client(
    url,
    key,
    options=ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
        schema="public",
    ),
)


class Table:
    pass


class TableRegistry(str):
    DataRegistry = "data_registry"
    ToolRegistry = "tool_registry"

    pass


class SupaBase:
    @staticmethod
    async def execute(queries: list[str]) -> list[any]:  # 2. execute query
        datas = []
        for query in queries:
            try:
                response = supabase_client.rpc(
                    "execute_raw_query", {"query": query}
                ).execute()
                if response.data:
                    datas.append(response.data)
            except Exception as e:
                datas.append(f"Error: {e}")

        return datas
