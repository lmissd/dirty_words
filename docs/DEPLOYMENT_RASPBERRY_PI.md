# 树莓派部署说明

## 1. 烧录系统

使用 Raspberry Pi Imager 烧录 Raspberry Pi OS 64-bit。

推荐设置：

- 主机名：`yuangungun`
- 用户名：`pi`
- WiFi：填写家庭或实验网络
- SSH：开启

## 2. 首次连接

同一局域网下尝试：

```bash
ssh pi@yuangungun.local
```

如果 `.local` 不可用，请在路由器后台查找树莓派 IP，然后使用：

```bash
ssh pi@树莓派IP地址
```

## 3. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip portaudio19-dev libsndfile1 alsa-utils
```

如需播放 TTS 生成的音频，也可安装：

```bash
sudo apt install -y mpg123 ffmpeg
```

如需使用 Piper 中文神经 TTS，也建议安装：

```bash
sudo apt install -y piper
```

如果你的系统源里没有 `piper`，也可以用官方发布包：

```bash
cd ~
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz
tar -xzf piper_linux_aarch64.tar.gz
sudo install -m 755 piper/piper /usr/local/bin/piper
```

## 4. 克隆项目

```bash
git clone https://github.com/lmissd/dirty_words.git
cd dirty_words
```

## 5. 创建 Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. 配置密钥和参数

```bash
cp config/config.example.yaml config/config.yaml
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

编辑 `config/config.yaml`，根据麦克风、屏幕和喇叭情况调整参数。

如果你要用 Piper 中文神经 TTS：

1. 准备 Piper 中文模型，例如 `zh_CN-huayan-medium.onnx` 和对应的 `zh_CN-huayan-medium.onnx.json`
2. 放到项目目录：

```text
models/piper/
```

3. 确认配置：

```yaml
greeting:
  use_prerecorded_audio: false

tts:
  provider: "piper"
  binary: "piper"
  model_path: "models/piper/zh_CN-huayan-medium.onnx"
  model_config_path: "models/piper/zh_CN-huayan-medium.onnx.json"
```

4. 下载中文模型：

```bash
mkdir -p models/piper
cd models/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
```

## 7. 预览唤醒动画

接好 HDMI 屏幕后，可以先单独播放一次小机器人唤醒动画：

```bash
source .venv/bin/activate
python scripts/play_wake_animation.py --config config/config.yaml --duration 3
```

这个预览不依赖麦克风、唤醒模型或音频播放。如果只想在桌面窗口里测试，可以加上 `--windowed`。

## 8. 运行

```bash
source .venv/bin/activate
python main.py --config config/config.yaml
```

第一版默认使用控制台唤醒和控制台显示，方便验证流程。接入真实硬件后，将 `display.engine` 改为 `robot_animation`，并根据需要调整录音设备。

## 9. 开机自启动预留

后续可以新增 systemd 服务文件，例如：

```text
/etc/systemd/system/civil-language-robot.service
```

第一阶段先手动运行并验证麦克风、喇叭、屏幕和 API 调用稳定后，再启用自启动。
