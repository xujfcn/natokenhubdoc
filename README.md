# TokenLab API 中文文档

这是 [TokenLab](https://na.tokenlab.sh/) 的中文调用文档，使用 Mintlify 格式编写，面向需要通过 OpenAI 兼容接口调用 `gpt-6-astra` 的开发者。

## 本地预览

安装 [Mintlify CLI](https://www.mintlify.com/docs/quickstart)，然后在本目录运行：

```bash
mintlify dev
```

## 实际验证

仓库包含 `scripts/verify_api.py`，会验证模型列表、非流式对话和 SSE 流式对话。不要把 API Key 写入文件，运行前设置环境变量：

```bash
# PowerShell
$env:TOKENLAB_API_KEY = "sk-..."
python scripts/verify_api.py

# bash
export TOKENLAB_API_KEY="sk-..."
python3 scripts/verify_api.py
```

验证脚本默认只请求 `https://na.tokenlab.sh`，不会输出完整密钥。

Responses API 的普通和流式验证：设置同一环境变量后运行 `python scripts/verify_responses.py`。该脚本不自动重试，校验实际文本、响应状态、用量和 `response.completed` 事件。

SDK 示例验证会直接提取两个 SDK 文档页中的代码并执行，不另行维护替代示例：

```bash
python -m pip install openai==2.35.1
npm ci
python scripts/verify_sdk_examples.py
```

可以用 `--sdk python` 或 `--sdk node` 单独验证。SDK 页的两段代码在同一个进程内顺序运行；Node.js 使用 ESM（保存为 `.mjs` 或在 `package.json` 中设置 `"type": "module"`）。
