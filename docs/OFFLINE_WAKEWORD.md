# 本地离线唤醒说明

## 当前实现

项目新增 `wakeword.engine: "vosk"`，使用 Vosk 中文离线模型在树莓派本地监听唤醒词。

默认唤醒词：

```text
范小团
```

待机监听阶段不调用 OpenAI，也不调用 DeepSeek。

## 工作流程

```text
麦克风持续输入
↓
Vosk 中文模型本地识别
↓
检查文本是否包含“范小团”
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
  wake_words:
    - "范小团"
  model_path: "models/vosk-model-small-cn-0.22"
  sample_rate: 16000
  channels: 1
  device: 3
  block_size: 8000
  grammar_enabled: true
```

如果 `python scripts/list_audio_devices.py` 显示 USB 麦克风不是设备 `3`，请同步修改：

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
范小团
```

如果显示“唤醒成功”，说明本地离线唤醒可用。

## 测试唤醒后问候

```bash
python main.py --config config/config.yaml --wake-greeting --once
```

注意：这个模式的唤醒是离线的，但当前问候语播报仍使用配置中的 TTS 服务。

## 测试完整流程

```bash
python main.py --config config/config.yaml --once
```

这时：

```text
本地离线 Vosk 负责唤醒
OpenAI Speech-to-Text 负责唤醒后的语音转文字
DeepSeek 负责文明用语分析
OpenAI TTS 负责语音播报
```

## 局限

Vosk 是通用中文语音识别，不是专门训练的“范小团”唤醒词模型。第一版可用于离线验证，但误触发率和唤醒成功率需要实测调整。正式长期版本可以继续升级为专用唤醒词模型。
