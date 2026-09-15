# Qweather-Agent：基于和风天气的智能体

Qweather-Agent 是一个基于大模型 Function Calling（函数调用）能力与和风天气 API 的智能体。它通过 DeepSeek 的对话接口理解用户意图，自动判断是否需要调用天气查询工具，并将工具返回的结构化天气数据转化为自然语言回答，可用于根据天气信息进行决策（如出行建议、穿衣推荐等）。

## 功能特性

- **对话式天气查询**：直接用自然语言提问，如「北京明天天气怎么样？需要带伞吗？」
- **Function Calling**：模型自主判断是否调用 `get_weather` 工具，支持多轮对话记忆
- **基于和风天气 API**：
  - 城市地理查询（GeoAPI）将城市名解析为经纬度
  - 每日天气预报（1～10 天）：温度、白天/夜间天气、风力、降水概率、湿度、日出日落等
- **完善的错误处理**：城市未找到、请求超时、HTTP 错误等均会返回结构化错误信息给模型，由模型组织友好回复

## 工作原理

1. 用户输入消息，连同工具列表一起发送给 DeepSeek 模型
2. 模型判断是否需要调用 `get_weather` 工具
3. 若需要调用，Agent 执行工具链：
   - 调用和风天气 GeoAPI，将城市名解析为经纬度
   - 调用和风天气每日天气预报 API 获取未来天气数据
4. 将工具结果（JSON）回传给模型，模型生成自然语言回答

## 项目结构

```
Qweather-Agent/
├── main.py                      # 主程序：对话循环 + Function Calling 逻辑
├── utils/
│   ├── __init__.py
│   └── tool_get_weather.py      # 和风天气查询工具（城市查询 + 每日预报）
├── .env                         # 环境变量配置（API Key 等，需自行填写）
├── requirements.txt             # Python 依赖
└── README.md
```

## 环境要求

- Python 3.10+
- DeepSeek API Key
- 和风天气 API Key 及专属 API Host

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑项目根目录下的 `.env` 文件：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
BASE_URL=https://api.deepseek.com

WEATHER_API_KEY=your_qweather_api_key
WEATHER_API_HOST=your_qweather_api_host
```

| 环境变量 | 说明 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek 开放平台 API Key |
| `BASE_URL` | DeepSeek API 地址，默认 `https://api.deepseek.com` |
| `WEATHER_API_KEY` | 和风天气控制台的 API Key |
| `WEATHER_API_HOST` | 和风天气控制台「设置」中的专属 API Host（不含 `https://` 前缀也可自动处理） |

- DeepSeek API Key：[DeepSeek 开放平台](https://platform.deepseek.com/) 创建
- 和风天气凭据：[和风天气开发者控制台](https://console.qweather.com/) 创建项目并获取 API Key 与 API Host

### 3. 运行

```bash
python main.py
```

启动后在终端输入消息即可对话，输入 `q` 退出。

## 使用示例

```
[人设] 你是一个友好的助手，可以查询天气。请记住用户告诉你的信息。
输入消息开始聊天，输入 q 退出

用户: 北京未来三天天气怎么样？
  [调用工具] get_weather({'city': '北京'}) => {"success": true, "city": "北京", ...}
AI: 北京未来三天以晴到多云为主，最高气温 25°C，最低 14°C，昼夜温差较大，建议早晚适当添加衣物……

用户: 那需要带伞吗？
AI: 从预报来看，未来三天降水概率较低，一般不需要带伞……
```

## 工具说明

### `get_weather(city)`

查询中国城市未来天气。

- **参数**：`city`（string，必填）——城市名称，如「北京」「杭州」
- **返回**：JSON 字符串，包含城市名、所属省份、逐日预报（日期、最高/最低温度、白天/夜间天气、风力等级、降水概率、湿度、日出日落时间）及数据来源信息
- 查询失败时返回 `{"success": false, "error": "..."}`，由模型向用户解释原因
