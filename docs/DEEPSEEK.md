# DeepSeek API 配置说明

## 作用范围

DeepSeek API 当前用于替换“文明用语分析”模块，也就是：

```text
用户原话 -> 是否文明 -> 文明评分 -> 原因 -> 改写建议
```

语音转文字和 TTS 仍需要 OpenAI 或其他语音服务。

## 官方接口

DeepSeek API 兼容 OpenAI SDK。项目使用：

```text
base_url: https://api.deepseek.com
api key 环境变量：DEEPSEEK_API_KEY
推荐模型：deepseek-v4-flash
```

## 配置步骤

复制配置：

```bash
cp config/raspberry-pi.example.yaml config/config.yaml
cp .env.example .env
```

编辑 `.env`：

```bash
nano .env
```

填入：

```text
OPENAI_API_KEY=你的 OpenAI API Key
DEEPSEEK_API_KEY=你的 DeepSeek API Key
```

编辑 `config/config.yaml`，确认：

```yaml
llm:
  provider: "deepseek"
  model: "deepseek-v4-flash"
  temperature: 0.2
  max_tokens: 500
```

同时确认：

```yaml
deepseek:
  api_key_env: "DEEPSEEK_API_KEY"
  base_url: "https://api.deepseek.com"
```

## 运行

测试完整闭环：

```bash
python main.py --config config/config.yaml --once
```

如果只测试唤醒词：

```bash
python main.py --config config/config.yaml --wakeword-only
```

注意：`--wakeword-only` 使用 STT 唤醒时仍需要 `OPENAI_API_KEY`，因为当前唤醒词识别依赖语音转文字。
