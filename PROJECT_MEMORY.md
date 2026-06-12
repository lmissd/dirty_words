# 项目记忆：文明用语机器人

## 当前项目

项目名称：文明用语机器人（Civil Language Robot）

GitHub 仓库：

```text
https://github.com/lmissd/dirty_words.git
```

这是一个基于 Raspberry Pi 4B 的桌面 AI 机器人项目。机器人通过语音与用户交互，对用户语言进行文明程度检测，并对不文明表达进行提醒和改写建议。

## 设备信息

```text
主控：Raspberry Pi 4B
系统：Raspberry Pi OS 64-bit
主机名：yuangungun
用户：pi
网络：WiFi 联网
SSH：开启
```

密码已由用户在 Raspberry Pi Imager 中设置。出于安全原因，不在 Git 仓库或项目记忆文件中保存明文密码。

## 硬件组成

- 输入设备：双麦克风阵列，USB 麦克风兼容方案
- 输出设备：喇叭，功放模块
- 显示设备：HDMI 显示屏
- 存储：MicroSD 卡

## 项目目标

开发一个长期待机的桌面 AI 机器人。机器人被唤醒后录音，调用云端语音识别服务得到文本，再调用大模型 API 分析表达是否文明，最后通过屏幕显示和语音播报给出提醒与文明表达建议。

项目采用云端大模型 API 方案，不在树莓派本地运行大模型。

## 默认交互流程

```text
待机
监听唤醒词
被唤醒
录音
语音转文字
文明分析
显示结果
语音播报
返回待机
```

## 核心功能

- 语音唤醒：当前用户希望默认唤醒词为“范小团”。第一阶段先使用 STT 语音唤醒方案，后续可替换为离线关键词唤醒。
- 录音：唤醒成功后录制 5-10 秒临时音频。
- 语音识别：调用云端 Speech-to-Text 服务，推荐 OpenAI Speech-to-Text。
- 文明分析：调用 GPT 类大模型，返回 JSON，包括是否文明、评分、原因和建议。
- 屏幕显示：显示用户原话、文明评分、分析结果和改写建议，中文优先、大字体、全屏。
- 语音播报：调用 TTS 接口播报分析结果和建议。

## 开发原则

- 模块化设计
- 易维护
- 易扩展
- 面向未来升级
- 所有配置独立存放
- 所有 API 密钥统一管理
- 所有功能组件解耦

## 协作规则

每完成一个模块或阶段性功能后，先交给用户在本地或树莓派上验证是否可行。用户确认可行后，再询问用户是否要提交 Git。不要在功能刚改完、用户尚未验证前直接提交。

## 技术选择

- Python 3.11+
- Raspberry Pi OS 64-bit
- OpenAI API 用于语音识别和 TTS
- DeepSeek API 可用于文明用语分析
- Git + GitHub 版本控制
- systemd 后台自启动

## 项目结构要求

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

## 配置与安全

真实配置文件 `config/config.yaml` 不入库。公开仓库只保留 `config/config.example.yaml`。

API Key、树莓派密码和其他敏感信息不写入代码、不写入 README、不提交 GitHub。需要本地保存时使用被 `.gitignore` 忽略的文件，例如 `.env` 或 `LOCAL_CREDENTIALS.md`。

## 第一阶段目标

实现完整闭环：

1. 唤醒词检测
2. 录音
3. 语音识别
4. GPT 文明分析
5. 屏幕显示
6. 语音播报

## 第二阶段预留能力

- 摄像头
- 表情识别
- 情绪分析
- 本地知识库
- 联网查询
- 微信通知
- 多角色人格
- 长期记忆
- 远程管理后台

## 当前下一步

当前 USB 音响麦克风一体设备在树莓派 ALSA 中识别为 `card 3, device 0`，录音和播放测试已经可以听到回放。下一步在树莓派上复制 `config/raspberry-pi.example.yaml` 为 `config/config.yaml`，配置 OpenAI API Key，测试 `python main.py --config config/config.yaml --wakeword-only`，说“范小团”触发语音唤醒。

用户希望先实现第一步唤醒反馈：识别到“范小团”后暂时不进入脏话检测流程，只显示唤醒成功并播放“小朋友你好”。对应运行命令为 `python main.py --config config/config.yaml --wake-greeting --once`。

用户进一步明确希望“范小团”的待机唤醒在本地离线完成，只有被唤醒后再调用云端服务做后续识别和文明分析。当前实现方向是新增 `wakeword.engine: "vosk"`，使用 Vosk 中文离线模型 `models/vosk-model-small-cn-0.22` 在树莓派本地监听唤醒词。
