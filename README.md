# 文明用语机器人

Civil Language Robot 是一个基于 Raspberry Pi 4B 的桌面 AI 机器人项目。

机器人通过语音与用户交互，识别用户表达的文明程度，并对不文明表达进行温和提醒和改写建议。项目采用云端大模型 API 方案，不在树莓派本地运行大模型。

## 核心闭环

```text
待机 -> 监听唤醒词 -> 录音 -> 语音转文字 -> 文明分析 -> 屏幕显示 -> 语音播报 -> 返回待机
```

## 硬件环境

- 主控：Raspberry Pi 4B
- 系统：Raspberry Pi OS 64-bit
- 主机名：yuangungun
- 用户：pi
- 网络：WiFi
- 远程访问：SSH
- 输入：双麦克风阵列，USB 麦克风兼容方案
- 输出：喇叭，功放模块
- 显示：HDMI 显示屏
- 存储：MicroSD 卡

## 软件架构

项目采用模块化设计，所有核心能力都通过接口解耦：

```text
main.py
config/
modules/
  wakeword/
  recorder/
  speech_to_text/
  llm/
  tts/
  display/
  utils/
assets/
logs/
tests/
docs/
```

## 第一阶段目标

第一阶段实现完整功能闭环：

- 语音唤醒
- 录音
- 云端语音识别
- GPT 文明用语分析
- 屏幕显示结果
- 语音播报提醒和改写建议

## 配置与密钥

真实配置文件使用：

```text
config/config.yaml
```

该文件已被 Git 忽略，不会提交到 GitHub。请从示例文件复制：

```powershell
Copy-Item config/config.example.yaml config/config.yaml
Copy-Item .env.example .env
```

然后在 `.env` 或系统环境变量中设置：

```text
OPENAI_API_KEY=你的 OpenAI API Key
DEEPSEEK_API_KEY=你的 DeepSeek API Key
```

不要把真实 API Key、树莓派密码或其他凭据提交到仓库。

## 本地开发

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests
python main.py --config config/config.yaml
```

Windows 本地开发默认使用控制台唤醒和控制台显示，方便先跑通逻辑。部署到树莓派后，可在配置中切换到真实麦克风录音、HDMI 全屏显示和音频播放。

## 第一阶段：唤醒词验证

在还没有配置 OpenAI API Key 前，可以只测试唤醒词模块：

```bash
python main.py --config config/config.example.yaml --wakeword-only
```

当前默认是控制台模拟唤醒。看到提示后输入：

```text
小文小文
```

如果显示“唤醒成功”，说明项目的唤醒词流程已经打通。接下来再测试麦克风录音，并把唤醒词引擎替换为真实语音唤醒实现。

树莓派上要测试真实语音唤醒时，使用：

```bash
cp config/raspberry-pi.example.yaml config/config.yaml
cp .env.example .env
python scripts/list_audio_devices.py
python main.py --config config/config.yaml --wakeword-only
```

默认语音唤醒词是：

```text
范小团
```

## 文档

- [项目总规范](docs/PROJECT_SPEC.md)
- [架构说明](docs/ARCHITECTURE.md)
- [语音唤醒测试说明](docs/VOICE_WAKEWORD.md)
- [DeepSeek API 配置说明](docs/DEEPSEEK.md)
- [树莓派部署说明](docs/DEPLOYMENT_RASPBERRY_PI.md)
- [安全说明](docs/SECURITY.md)
