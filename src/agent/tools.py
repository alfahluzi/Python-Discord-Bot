from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import ShellTool
from langchain_experimental.tools.python.tool import PythonREPLTool


class StaticTools:
    duckduckgo_tool = Tool(
        name="DuckDuckGo Search",
        func= DuckDuckGoSearchRun().run,
        description="Gunakan ini untuk mencari informasi terbaru atau fakta di internet. Contoh pertanyaan: 'Siapa presiden Indonesia saat ini?' atau 'Berita terbaru tentang AI'."
    )
    python_tool = PythonREPLTool()
    shell_tool = ShellTool()


    tools = [duckduckgo_tool, python_tool, shell_tool]
