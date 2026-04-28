import re
import sys
from pathlib import Path

import tools.ToolExecutor as ToolExecutor
from tools.HelloAgentsLLM import HelloAgentsLLM

class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        template_path = Path(__file__).with_name("REACT_PROMPT_TEMPLATE.md")
        return template_path.read_text(encoding="utf-8")

    def _parse_output(self, text: str):
        """解析LLM的输出，提取Thought和Action。
        """
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 默认匹配到文本末尾；若后续还有独立 Finish，则只取 Action 到 Finish 前的内容
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        if action and not action.startswith("Finish"):
            finish_match = re.search(r"\s+Finish\b", action)
            if finish_match:
                action = action[:finish_match.start()].strip()
        return thought, action

    def _parse_action(self, action_text: str):
        """解析Action字符串，提取工具名称和输入。
        """
        match = re.match(r"\{?(\w+)\}?\[(.*)\]", action_text, re.DOTALL)
        if match:
            tool_input = match.group(2).strip()
            if len(tool_input) >= 2 and tool_input[0] == tool_input[-1] and tool_input[0] in ("'", '"'):
                tool_input = tool_input[1:-1]
            return match.group(1), tool_input
        return None, None

    def run(self, question: str):
        """
        运行ReAct智能体来回答一个问题。
        """
        self.history = [] # 每次运行时重置历史记录
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- 第 {current_step} 步 ---")

            # 1. 格式化提示词
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = self.prompt_template.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )
            
            # 2. 调用LLM进行思考
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            
            if not response_text:
                print("错误:LLM未能返回有效响应。")
                break

            # 3. 解析LLM的输出
            thought, action = self._parse_output(response_text)
            
            if thought:
                print(f"思考: {thought}")

            if not action:
                print("警告:未能解析出有效的Action，流程终止。")
                break

            # 4. 执行Action
            finish_match = re.search(r"Finish\[(.*?)\]", response_text, re.DOTALL)
            if finish_match:
                # 如果响应中包含Finish指令，提取最终答案并结束
                final_answer = finish_match.group(1).strip()
                print(f"🎉 最终答案: {final_answer}")
                return final_answer
            
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # ... 处理无效Action格式 ...
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            
            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"错误:未找到名为 '{tool_name}' 的工具。"
            else:
                observation = tool_function(tool_input) # 调用真实工具

            print(f"👀 观察: {observation}")
            
            # 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        # 循环结束
        print("已达到最大步数，流程终止。")
        return None


if __name__ == "__main__":
    llm_client = HelloAgentsLLM()
    tool_executor = ToolExecutor.ToolExecutor()
    tool_executor.registerTool(
        name="search",
        description="一个基于SerpApi的网页搜索工具，输入查询语句，返回智能解析的搜索结果。",
        func=ToolExecutor.search,
    )

    agent = ReActAgent(llm_client=llm_client, tool_executor=tool_executor)
    result = agent.run("2026年华为最新手机型号及主要卖点")
    print(f"运行结果: {result}")
