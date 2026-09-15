import os
import json
from openai import OpenAI
import dotenv
import utils.tool_get_weather as tool_get_weather

dotenv.load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("BASE_URL")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# 工具列表
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

def get_weather(city):
    """
    查询指定城市的当前天气
    """
    data = tool_get_weather.get_daily_weather(city)
    return json.dumps(data, ensure_ascii=False)

# 工具名到函数的映射
tool_functions = {"get_weather": get_weather}

SYSTEM_PROMPT = "你是一个友好的助手，可以查询天气。请记住用户告诉你的信息。"
messages = [{"role": "system", "content": SYSTEM_PROMPT}]

print(f"[人设] {SYSTEM_PROMPT}")
print("输入消息开始聊天，输入 q 退出\n")

while True:
    user_input = input("用户: ")
    if user_input.strip() == "q":
        break

    messages.append({"role": "user", "content": user_input})

    # 把工具列表传给 API，模型会自己判断是否需要调用
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        tools=tools,
        extra_body={"reasoning_effort": "high"}
        # extra_body={"thinking": {"type": "disabled"}}
    )
    assistant_message = response.choices[0].message

    # 如果模型决定调用工具
    if assistant_message.tool_calls:
        messages.append(assistant_message)
        for tool_call in assistant_message.tool_calls:
            # arguments 是 JSON 字符串，需要解析成字典
            args = json.loads(tool_call.function.arguments)
            # **args 把字典解包成关键字参数，等价于 func(city="北京")
            func = tool_functions[tool_call.function.name]
            result = func(**args)
            print(f"  [调用工具] {tool_call.function.name}({args}) => {result}")
            # role 为 "tool" 表示这是工具返回的结果
            # tool_call_id 用来关联这条结果对应哪个工具调用
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
        # 拿到工具结果后再调一次模型，让它生成自然语言回答
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            extra_body={"reasoning_effort": "high"}
            # extra_body={"thinking": {"type": "disabled"}}
        )
        assistant_message = response.choices[0].message

    messages.append({"role": "assistant", "content": assistant_message.content})
    print(f"AI: {assistant_message.content}\n")