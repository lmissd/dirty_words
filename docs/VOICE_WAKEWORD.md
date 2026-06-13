# 语音唤醒测试说明

## 当前方案

早期版本支持 STT 语音唤醒：

```text
短录音片段 -> 语音转文字 -> 检查是否包含唤醒词 -> 命中后进入主流程
```

默认唤醒词：

```text
范小团你好
```

这个方案适合快速验证完整闭环，但它会持续调用云端语音识别 API。现在项目已新增 Vosk 本地离线唤醒，长期待机建议优先使用 `wakeword.engine: "vosk"`。

本地离线唤醒详见：

```text
docs/OFFLINE_WAKEWORD.md
```

## 树莓派配置

你当前的 USB 音响麦克风一体设备被 ALSA 识别为：

```text
card 3, device 0
```

树莓派配置示例文件：

```text
config/raspberry-pi.example.yaml
```

首次部署时复制：

```bash
cp config/raspberry-pi.example.yaml config/config.yaml
cp .env.example .env
```

然后编辑 `.env`，填入：

```text
OPENAI_API_KEY=你的 OpenAI API Key
DEEPSEEK_API_KEY=你的 DeepSeek API Key
```

当前树莓派示例配置中，语音识别和 TTS 仍使用 OpenAI，文明用语分析使用 DeepSeek。

## 确认 Python 音频设备

ALSA 的 `card 3` 不一定总是等于 Python `sounddevice` 的设备编号，而且断电重启或重新插拔 USB 设备后编号也可能变化。当前树莓派配置默认使用：

```yaml
wakeword:
  device: "auto"

recording:
  device: "auto"
```

程序会优先自动选择带输入通道的 USB 麦克风。建议执行下面命令查看当前设备列表和自动选择结果：

```bash
python scripts/list_audio_devices.py --config config/config.yaml
```

如果自动选择不符合预期，再临时手动指定：

```yaml
wakeword:
  device: 真实的 Python 输入设备编号

recording:
  device: 真实的 Python 输入设备编号
```

播放设备也建议自动选择：

```yaml
playback:
  alsa_device: "auto"
```

## 只测试唤醒词

```bash
python main.py --config config/config.yaml --wakeword-only
```

运行后对着麦克风说：

```text
范小团你好
```

如果终端显示“唤醒成功”，说明语音唤醒链路已打通。

## 测试完整闭环

```bash
python main.py --config config/config.yaml --once
```

流程：

```text
说“范小团你好”
等待系统提示已唤醒
继续说一句要分析的话
系统转文字
系统调用大模型判断文明程度
系统显示结果
系统语音播报建议
```

## 测试唤醒问候

如果只想测试“范小团你好”触发后的问候，不进入文明分析：

```bash
python main.py --config config/config.yaml --wake-greeting --once
```

流程：

```text
说“范小团你好”
系统显示“唤醒成功”
系统播报“小朋友你好”
程序结束
```

如果想持续待机并重复问候：

```bash
python main.py --config config/config.yaml --wake-greeting
```
