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

- 语音唤醒：当前用户希望默认触发句为“范小团你好”。待机唤醒应使用本地离线方案，后续才调用云端服务。
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

当前 USB 音响麦克风一体设备在树莓派 ALSA 中识别为 `card 3, device 0`，采样率使用 `48000`，录音和播放测试已经可以听到回放。为避免断电重启或重新插拔后 Python `sounddevice` 设备编号变化，树莓派配置默认使用 `device: "auto"` 自动查找有输入通道的 USB 麦克风。测试离线唤醒时运行 `python main.py --config config/config.yaml --wakeword-only`，说“范小团你好”触发。

用户希望先实现第一步唤醒反馈：识别到“范小团你好”后暂时不进入脏话检测流程，只显示唤醒成功并播放“小朋友你好”。对应运行命令为 `python main.py --config config/config.yaml --wake-greeting --once`。

用户进一步明确希望“范小团”的待机唤醒在本地离线完成，只有被唤醒后再调用云端服务做后续识别和文明分析。当前实现方向是新增 `wakeword.engine: "vosk"`，使用 Vosk 中文离线模型 `models/vosk-model-small-cn-0.22` 在树莓派本地监听唤醒词。用户希望触发句改为“范小团你好”，并支持模糊识别：识别文本需要包含“你好/你号”类问候，并且出现“小团”或接近“范小团”的词。

用户希望唤醒问候也不要依赖 OpenAI Key。当前方向是新增 `tts.provider: "local_audio"`，问候模式播放本地 `assets/audio/greeting.wav`。如果没有真人语音文件，先用 `scripts/generate_greeting_audio.py` 生成离线提示音占位；后续可替换为真正的“小朋友你好”录音。

用户进一步要求问候要真正说出“小朋友你好”，而不是提示音。当前方向是新增 `tts.provider: "local_command"`，通过树莓派本地 `espeak-ng` 生成 `assets/audio/greeting.wav` 并播放。该方案完全离线，但音色会偏机器人感。

当前新升级方向是唤醒问候优先使用用户自己的预设录音。树莓派配置使用 `greeting.use_prerecorded_audio: true`，问候模式会直接播放 `greeting.audio_path`，默认路径为 `assets/audio/greeting.wav`。用户可在树莓派运行 `python scripts/record_greeting_audio.py --config config/config.yaml --duration 3 --playback` 录制自己的“小朋友你好”。该音频属于个人/测试文件，不提交 GitHub。

录制预设问候时，如果出现 `aplay ... plughw:3,0 ... No such file or directory`，说明录音已保存但试听播放设备配置不稳定。播放端也应使用自动选择：`playback.alsa_device: "auto"`。程序会自动选择有输出通道的设备，避免 USB 设备当前只有输入通道时仍固定使用 `plughw:3,0`。

树莓派连接蓝牙音箱后，`wpctl status` 中可见蓝牙输出 `F7`，并且它是默认 sink。播放预设问候音频时应优先使用 PipeWire 的 `pw-play`，这样声音会进入当前默认蓝牙音箱；不要优先走 `aplay`，否则可能被自动选到 3.5mm `Headphones` 而听不到蓝牙音箱声音。

用户新增一张小机器人连续动作图：`pics/fantuan_robot.png`。当前已将其作为 `2 行 x 4 列` 精灵图处理，生成透明背景整图 `assets/robot/fantuan_robot_transparent.png`，并拆分出 `assets/robot/fantuan_jump/frame_00.png` 到 `frame_07.png`。最小可运行版本使用 `display.engine: "robot_animation"`，唤醒成功后播放约 10 秒跳跃动画，然后停留在 `final_frame: 7` 的微笑站立帧。

唤醒问候流程中，动画和预设语音应同时开始：检测到“范小团你好”后，后台线程播放 `assets/audio/greeting.wav`，主线程同时播放机器人跳跃动画。动画结束后保持微笑帧，再回到待机循环。

用户要求运行逻辑为持续待机、可重复触发。被“范小团你好”唤醒后，如果 30 秒内没有检测到新的语音活动，系统自动恢复待机，不进入后续录音、语音识别或大模型分析。该逻辑通过 `post_wake_speech.timeout_seconds: 30` 配置。

## 当前已验证状态

截至 2026-06-13，树莓派 `yuangungun` 上的当前阶段目标是测试离线唤醒问候闭环：持续待机，用户说“范小团你好”，本地 Vosk 离线识别唤醒，树莓派使用用户自己录制的 `assets/audio/greeting.wav` 播放“小朋友你好”，同时在 HDMI 屏幕播放约 10 秒小机器人跳跃动画，随后停留在微笑帧并返回待机继续监听。这个阶段暂时不需要 OpenAI API Key，也暂时不进入文明分析流程。

树莓派项目目录为 `/home/pi/dirty_words`，虚拟环境为 `/home/pi/.venv`。当前测试命令：

```bash
cd ~/dirty_words
source ~/.venv/bin/activate
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 python main.py --config config/config.yaml --wake-greeting
```

如果直接在树莓派桌面终端中运行，可省略 `DISPLAY` 和 `XDG_RUNTIME_DIR`。如果通过 SSH 启动机器人动画显示，必须带上这两个环境变量，否则会报“无法打开机器人动画窗口”。

当前播放链路优先使用 PipeWire 的 `pw-play`，让语音进入默认蓝牙音箱 `F7`；麦克风仍由自动选择的 USB 输入设备负责。

如果再次出现 `Invalid number of channels [PaErrorCode -9998]`，优先检查是否有旧的唤醒测试进程占用麦克风。可用下面命令清理后重试：

```bash
pkill -9 -f "main.py --config config/config.yaml --wake-greeting"
fuser -v /dev/snd/* 2>&1 || true
python scripts/list_audio_devices.py --config config/config.yaml
```

期望 `python scripts/list_audio_devices.py --config config/config.yaml` 能看到 USB 设备为 `1 in, 2 out`，并显示自动选择的麦克风 `device`。如果显示 `0 in, 2 out`，通常说明麦克风被旧进程占用或 USB 音频设备需要重新插拔。

## 临时文件清理规则

测试过程中生成的临时录音、唤醒片段、TTS 音频缓存和模型压缩包不要长期堆在项目目录里。默认应保持 `privacy.keep_recordings: false`，让正式流程处理完录音后自动删除；STT 唤醒片段保持 `wakeword.delete_chunks: true`。手动测试后如产生 `recordings/*.wav`、`assets/audio/*.wav`、`assets/audio/*.mp3`、日志文件或临时下载文件，应确认不再需要后及时删除，避免测试文件越来越多导致目录混乱。仓库中只保留 `.gitkeep`、代码、配置示例、文档和必要测试，不提交临时音频或真实凭据。
