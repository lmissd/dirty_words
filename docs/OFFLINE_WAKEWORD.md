# 本地离线唤醒说明

## 当前方案

项目支持两种本地离线唤醒方案：

- `wakeword.engine: "openwakeword"`：专用唤醒引擎，目标方案，用于“饭团饭团”。
- `wakeword.engine: "vosk"`：通用中文识别回退方案，用于没有自定义唤醒模型时继续测试。

当前目标唤醒词：

```text
饭团饭团
```

待机监听阶段不调用 OpenAI，也不调用 DeepSeek。

## openWakeWord 工作流程

```text
麦克风持续输入
↓
48kHz 单声道采集
↓
软件重采样到 16kHz
↓
按 80ms / 1280 samples 输入 openWakeWord
↓
VAD 过滤非语音噪声
↓
检测是否命中“饭团饭团”自定义模型
↓
命中后触发后续流程
```

openWakeWord 需要针对“饭团饭团”训练好的 `.onnx` 或 `.tflite` 模型文件。只安装 openWakeWord 库本身，不能自动识别任意中文唤醒词。

## 安装依赖

```bash
cd ~/dirty_words
source ~/.venv/bin/activate
pip install -r requirements.txt
```

如果树莓派 Python 3.13 安装 openWakeWord 时卡在 `tflite-runtime`，可以临时改用 ONNX 依赖链：

```bash
pip install onnxruntime scipy scikit-learn requests tqdm
pip install --no-deps openwakeword==0.6.0
```

项目配置默认使用：

```yaml
wakeword:
  inference_framework: "onnx"
```

## 放置 openWakeWord 自定义模型

将训练好的“饭团饭团”模型放到：

```text
models/openwakeword/fantuan_fantuan.onnx
```

模型文件已被 `.gitignore` 忽略，不会提交到 GitHub。

如果暂时还没有模型，可以把 `wakeword.engine` 临时改回 `vosk`，继续用旧方案测试问候动画和音频播放。

## 采集“饭团饭团”训练样本

在树莓派上使用新 Python 3.12 环境采集样本：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/collect_wakeword_samples.py --config config/config.yaml --count 30 --duration 2
```

脚本会每录一条提示一次：

```text
按回车开始录音；输入 q 退出；输入 s 跳过这个编号。
请准备说：饭团饭团
```

录完后默认询问是否保留、重录或删除跳过。建议至少录 `30-100` 条，录制时变化距离、音量和语速，例如近一点、远一点、正常说、小声说。默认保存目录：

```text
training_data/wakeword/fantuan_fantuan
```

采集脚本会自动生成 `metadata.csv`。这些文件属于个人训练素材，已被 `.gitignore` 忽略，不要提交 GitHub。

如果怀疑正样本里混入了噪音、空白或误录内容，可以逐条复听：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/review_positive_samples.py --config config/config.yaml
```

脚本会顺序播放正样本，并让你输入：

- `k`：保留
- `n`：标记为噪音，直接转移到 `training_data/wakeword/negative/review_noise`
- `r`：重播当前这一条
- `q`：退出

被标记为噪音的样本会自动从正样本目录移走，并更新正样本与负样本的 `metadata.csv`。

## 采集负样本

为了减少误触发，建议继续采集负样本。项目已提供：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/collect_negative_samples.py --config config/config.yaml --count 30 --duration 2 --playback
```

脚本会轮流提示三类负样本：

- `near_miss`：相似误触发词，例如“饭团你好”“饭桶饭桶”“范小团你好”
- `other_speech`：普通说话句子，例如“今天天气真不错”
- `ambient`：环境声，例如安静、不说话、轻敲桌面、翻书页

默认保存目录：

```text
training_data/wakeword/negative
```

建议至少录：

- 正样本 `30-100` 条
- 负样本 `30-100` 条

如果后续仍然误触发，再优先补充 `near_miss` 相似词负样本。

## 导出训练包

当正样本、负样本和复听清理都完成后，可以先把训练数据导出成一个独立压缩包，再拿去电脑或 Colab 训练 openWakeWord 自定义模型：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/export_wakeword_training_bundle.py --config config/config.yaml
```

默认会输出：

```text
exports/fantuan_fantuan_training_bundle.zip
```

压缩包内包含：

- `positive/`：正样本 WAV
- `negative/`：负样本 WAV
- `positive_metadata.csv`
- `negative_metadata.csv`
- `manifest.json`

这一步只是整理训练素材，不会自动生成 `models/openwakeword/fantuan_fantuan.onnx`。真正训练仍需使用 openWakeWord 官方训练流程。

## openWakeWord 配置

树莓派示例配置默认启用 openWakeWord：

```yaml
wakeword:
  engine: "openwakeword"
  display_wake_word: "饭团饭团"
  wake_words:
    - "饭团饭团"
  input_sample_rate: 48000
  model_sample_rate: 16000
  frame_ms: 80
  channels: 1
  device: "auto"
  model_paths:
    - "models/openwakeword/fantuan_fantuan.onnx"
  target_labels:
    - "fantuan_fantuan"
  threshold: 0.78
  patience_frames: 3
  debounce_seconds: 2.5
  rms_threshold: 180
  rms_patience_frames: 2
  inference_framework: "onnx"
  vad_enabled: true
  vad_threshold: 0.55
  noise_suppression_enabled: true
  noise_suppression_fallback: true
```

默认 `device: "auto"` 会自动选择带输入通道的 USB 麦克风设备，断电重启或重新插拔后不需要手动记住 Python 设备编号。可执行下面命令查看当前设备列表、程序自动选择结果，以及 48kHz 单声道输入是否可用：

```bash
python scripts/list_audio_devices.py --config config/config.yaml
```

## 只测试离线唤醒

```bash
python main.py --config config/config.yaml --wakeword-only
```

对麦克风说：

```text
饭团饭团
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
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 python main.py --config config/config.yaml --wake-greeting --once
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

完整分析流程默认会持续待机并支持重复触发。被“饭团饭团”唤醒后，系统会先等待用户继续说话：

```yaml
post_wake_speech:
  enabled: true
  timeout_seconds: 30
```

如果 30 秒内没有检测到新的语音活动，系统不会进入录音、语音识别或大模型分析，而是显示提示并自动返回待机。

这一步只做本地麦克风音量检测，不调用 OpenAI 或 DeepSeek。

## Vosk 回退方案

如果暂时没有“饭团饭团”的 openWakeWord 自定义模型，可以先改回：

```yaml
wakeword:
  engine: "vosk"
  display_wake_word: "范小团你好"
  wake_words:
    - "范小团你好"
  model_path: "models/vosk-model-small-cn-0.22"
  sample_rate: 48000
  channels: 1
  device: "auto"
  grammar_enabled: false
```

首次使用 Vosk 前下载中文模型：

```bash
python scripts/download_vosk_model.py
```

## 测试完整流程

```bash
python main.py --config config/config.yaml --once
```

这时：

```text
本地离线 openWakeWord 负责唤醒
OpenAI Speech-to-Text 负责唤醒后的语音转文字
DeepSeek 负责文明用语分析
本地音频或配置的 TTS 负责语音播报
```

## 局限

openWakeWord 的识别质量主要取决于“饭团饭团”自定义模型质量、麦克风距离、环境噪声和阈值。若没有自定义模型，项目只能使用 Vosk 回退方案；Vosk 是通用中文语音识别，不是专用唤醒模型，误触发率和唤醒成功率都可能不稳定。
