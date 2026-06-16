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
python scripts/list_audio_devices.py --config config/config.yaml
python main.py --config config/config.yaml --wakeword-only
```

当前目标语音唤醒词是：

```text
饭团饭团
```

当前树莓派示例配置默认使用 openWakeWord 专用本地唤醒链路：48kHz 单声道采集、软件重采样到 16kHz、80ms 音频帧、VAD 过滤背景声。openWakeWord 需要针对“饭团饭团”训练好的自定义模型：

```text
models/openwakeword/fantuan_fantuan.onnx
```

如果暂时还没有该模型，可以把 `wakeword.engine` 临时改回 `vosk`，并下载中文回退模型：

```bash
python scripts/download_vosk_model.py
python main.py --config config/config.yaml --wakeword-only
```

采集“饭团饭团”训练样本时，使用：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/collect_wakeword_samples.py --config config/config.yaml --count 30 --duration 2
```

脚本会每条录音前提示一次，录完后询问保留、重录或删除跳过。训练素材默认保存到 `training_data/wakeword/fantuan_fantuan`，不会提交到 GitHub。

如果正样本里混入了噪音或空白，可以逐条复听并把坏样本转到负样本目录：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/review_positive_samples.py --config config/config.yaml
```

为了减少误触发，还可以继续采集负样本：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/collect_negative_samples.py --config config/config.yaml --count 30 --duration 2 --playback
```

脚本会轮流提示相似误触发词、普通说话和环境声，默认保存到 `training_data/wakeword/negative`。

当正负样本都采集完成后，可以先导出一个训练包，便于复制到电脑或 Colab 做 openWakeWord 自定义模型训练：

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/export_wakeword_training_bundle.py --config config/config.yaml
```

默认会生成：

```text
exports/fantuan_fantuan_training_bundle.zip
```

压缩包内包含正样本、负样本、对应的 `metadata.csv` 快照和 `manifest.json`，这些素材不提交到 GitHub。

树莓派配置默认使用 `device: "auto"` 自动选择 USB 麦克风，断电重启或重新插拔后通常不需要手动修改设备编号。

如果只想测试“唤醒后问候”，不进入文明分析流程：

```bash
python scripts/play_wake_animation.py --config config/config.yaml --duration 3
python scripts/record_greeting_audio.py --config config/config.yaml --duration 3 --playback
python main.py --config config/config.yaml --wake-greeting --once
```

第一条命令会直接在 HDMI 屏幕上播放一次小机器人唤醒动画，不依赖麦克风、唤醒模型或问候音频，适合先单独确认屏幕和动画帧正常。

听到或识别到“饭团饭团”后，系统会显示唤醒成功，并播报：

```text
小朋友你好
```

当前树莓派配置默认优先播放你录制的本地音频 `assets/audio/greeting.wav`，不需要 OpenAI Key，也不需要本地 TTS。录制文件已被 Git 忽略，不会提交到 GitHub。

如果你想改成现成的中文神经语音包，项目现在也支持 Piper。把 `tts.provider` 改为 `piper`，并在 `tts.model_path` / `tts.model_config_path` 指向本地中文模型文件即可。这样打招呼和文明提醒都可以用同一个中文 TTS，不需要 OpenAI Key。

树莓派显示配置可使用 `display.engine: "robot_animation"`。唤醒成功后会播放 `assets/robot/fantuan_jump` 中的小机器人跳跃透明帧约 10 秒，并停留在微笑帧。

完整分析流程默认是持续待机、重复触发。被“饭团饭团”唤醒后，如果 30 秒内没有检测到新的语音活动，会自动返回待机，不进入语音识别和大模型分析。

## 文档

- [项目总规范](docs/PROJECT_SPEC.md)
- [架构说明](docs/ARCHITECTURE.md)
- [语音唤醒测试说明](docs/VOICE_WAKEWORD.md)
- [本地离线唤醒说明](docs/OFFLINE_WAKEWORD.md)
- [DeepSeek API 配置说明](docs/DEEPSEEK.md)
- [树莓派部署说明](docs/DEPLOYMENT_RASPBERRY_PI.md)
- [安全说明](docs/SECURITY.md)
