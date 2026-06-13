# 本地离线唤醒说明

## 当前实现

项目新增 `wakeword.engine: "vosk"`，使用 Vosk 中文离线模型在树莓派本地监听唤醒词。

默认唤醒词：

```text
范小团你好
```

待机监听阶段不调用 OpenAI，也不调用 DeepSeek。

## 工作流程

```text
麦克风持续输入
↓
Vosk 中文模型本地识别
↓
检查文本是否接近“范小团你好”
↓
命中后触发后续流程
```

## 安装依赖

```bash
cd ~/dirty_words
source .venv/bin/activate
pip install -r requirements.txt
```

## 下载离线中文模型

```bash
python scripts/download_vosk_model.py
```

默认会下载并解压到：

```text
models/vosk-model-small-cn-0.22
```

模型文件已被 `.gitignore` 忽略，不会提交到 GitHub。

## 配置

树莓派示例配置已经默认启用 Vosk 离线唤醒：

```yaml
wakeword:
  engine: "vosk"
  display_wake_word: "范小团你好"
  wake_words:
    - "范小团你好"
  wake_aliases:
    - "饭小团你好"
    - "办小团你好"
    - "但小团你好"
    - "分小团你好"
    - "小团你好"
  fuzzy_enabled: true
  require_greeting: true
  greeting_words:
    - "你好"
    - "你号"
  subject_keywords:
    - "小团"
  model_path: "models/vosk-model-small-cn-0.22"
  sample_rate: 48000
  channels: 1
  device: "auto"
  block_size: 8000
  grammar_enabled: false
```

默认 `device: "auto"` 会自动选择带输入通道的 USB 麦克风设备，断电重启或重新插拔后不需要手动记住 Python 设备编号。可执行下面命令查看当前设备列表和程序自动选择结果：

```bash
python scripts/list_audio_devices.py --config config/config.yaml
```

如果自动选择不符合预期，再临时手动指定：

```yaml
wakeword:
  device: 你的输入设备编号
```

## 只测试离线唤醒

```bash
python main.py --config config/config.yaml --wakeword-only
```

对麦克风说：

```text
范小团你好
```

如果显示“唤醒成功”，说明本地离线唤醒可用。

## 测试唤醒后问候

先录制你自己的固定问候语音：

```bash
python scripts/record_greeting_audio.py --config config/config.yaml --duration 3 --playback
```

录音会保存到：

```text
assets/audio/greeting.wav
```

然后测试唤醒后问候：

```bash
python main.py --config config/config.yaml --wake-greeting --once
```

这个模式的唤醒和问候播放都可以离线完成，不需要 OpenAI Key。树莓派配置默认播放你的预设录音：

```text
assets/audio/greeting.wav
```

这个录音文件属于个人/测试音频，已被 `.gitignore` 忽略，不要提交到 GitHub。如果想重新录制，重新运行 `scripts/record_greeting_audio.py` 覆盖即可。

树莓派显示可启用小机器人动画：

```yaml
display:
  engine: "robot_animation"

robot_animation:
  frame_dir: "assets/robot/fantuan_jump"
  duration_seconds: 10
  final_frame: 7
```

唤醒成功后，屏幕会播放约 10 秒跳跃动画，然后停留在微笑帧。动画帧来自 `pics/fantuan_robot.png`，已处理为透明背景并拆分到 `assets/robot/fantuan_jump`。

如果录音成功但试听播放失败，优先检查播放设备。树莓派配置默认使用：

```yaml
playback:
  prefer_pipewire: true
  alsa_device: "auto"
```

程序会优先使用 PipeWire 的默认输出，例如已连接的蓝牙音箱；如果 PipeWire 不可用，再自动选择有输出通道的 ALSA 设备，例如 USB 音箱、3.5mm 耳机口或 HDMI 音频。

## 唤醒后等待说话

完整分析流程默认会持续待机并支持重复触发。被“范小团你好”唤醒后，系统会先等待用户继续说话：

```yaml
post_wake_speech:
  enabled: true
  timeout_seconds: 30
```

如果 30 秒内没有检测到新的语音活动，系统不会进入录音、语音识别或大模型分析，而是显示提示并自动返回待机。

这一步只做本地麦克风音量检测，不调用 OpenAI 或 DeepSeek。

## 测试完整流程

```bash
python main.py --config config/config.yaml --once
```

这时：

```text
本地离线 Vosk 负责唤醒
OpenAI Speech-to-Text 负责唤醒后的语音转文字
DeepSeek 负责文明用语分析
本地音频或配置的 TTS 负责语音播报
```

## 局限

Vosk 是通用中文语音识别，不是专门训练的“范小团”唤醒词模型。第一版可用于离线验证，但误触发率和唤醒成功率需要实测调整。正式长期版本可以继续升级为专用唤醒词模型。
