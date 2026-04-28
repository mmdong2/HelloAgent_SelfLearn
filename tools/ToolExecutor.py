from typing import Dict, Any, Callable

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    # 工具注册方法
    def registerTool(self, name: str, description: str, func: Callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    #  获取工具方法
    def getTool(self, name: str) -> Callable|None:
        """
        根据名称获取一个工具的执行函数。
        self.tools.get(name, {})：如果 name 不存在，返回空字典 {}，不会抛 KeyError
        .get("func")：继续在结果字典中查找 "func"，若不存在则返回 None
        整条语句在 name 不存在 或 工具存在但缺 "func" 字段 时，都会安全返回 None
        """

        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])


##################################################################
# 工具: search 函数
##################################################################
from serpapi import SerpApiClient
import os

def search(query: str) -> str:
    """
    一个基于SerpApi的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。
    """
    print(f"🔍 正在执行 [SerpApi] 网页搜索: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误:SERPAPI_API_KEY 未在 .env 文件中配置。"

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",  # 国家代码
            "hl": "zh-cn", # 语言代码
        }
        
        client = SerpApiClient(params)
        results = client.get_dict()
        
        # 智能解析:优先寻找最直接的答案
        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # 如果没有直接答案，则返回前三个有机结果的摘要
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)
        
        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"
    


## 将 search 工具注册到 ToolExecutor 中，并模拟一次调用，以验证整个流程是否正常工作。
if __name__ == "__main__":
    toolExecutor = ToolExecutor()
    toolExecutor.registerTool(
        name="search",
        description="一个基于SerpApi的网页搜索工具，输入查询语句，返回智能解析的搜索结果。",
        func=search
    )

    # 模拟调用工具
    searchFunc = toolExecutor.getTool("search")
    if searchFunc:
        query = "Python编程语言的最新发展"
        result = searchFunc(query)
        print(f"搜索结果:\n{result}")
    else:
        print("工具 'search' 未找到。")