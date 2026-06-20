# 项目记忆：文明用语机器人（yuangungun）

## 1. 项目身份

- 项目名称：文明用语机器人（Civil Language Robot）
- 树莓派名称：`yuangungun`
- 树莓派用户：`pi`
- 最近一次确认的树莓派地址：`192.168.1.3`
- 本地仓库路径：`D:\Raspberry\dirty_words`
- 树莓派项目路径：`/home/pi/dirty_words`
- 树莓派 Python 虚拟环境：`/home/pi/.venv312`
- GitHub 仓库：`https://github.com/lmissd/dirty_words.git`
- 当前默认分支：`main`
- 最近一次已推送提交：`ff28f4c`
- 最近一次提交说明：`Add Tencent Cloud TTS and fix wake/TTS testing flow`

## 2. 用户协作偏好

- 全程使用中文沟通。
- 每完成一个模块后，先让用户在本地或树莓派验证是否可行，再询问是否提交 Git。
- 不要在用户还没确认效果前自动提交。
- 记忆文件要及时更新，避免上下文断档。
- 测试临时文件要主动清理，避免目录越来越乱。

## 3. 敏感信息与安全规则

- `.env` 属于高敏感文件，不要轻易覆盖。
- 本地 `.env` 路径：`D:\Raspberry\dirty_words\.env`
- 树莓派 `.env` 路径：`/home/pi/dirty_words/.env`
- 任何 `.env` 更新都必须遵守：
  - 先读取现有内容
  - 先做备份
  - 再写入新内容
- 不要把真实密钥提交到 GitHub。
- 不要把树莓派登录密码写入仓库、记忆文件或公开文档。
- 当前 `.env` 里至少应包含：
  - `DEEPSEEK_API_KEY`
  - `TENCENTCLOUD_SECRET_ID`
  - `TENCENTCLOUD_SECRET_KEY`

## 4. 当前树莓派真实运行方案（截至 2026-06-20）

当前可实际运行、已在树莓派上验证过的主方案如下：

- 唤醒方式：`wakeword.engine: stt`
- 唤醒词：`饭团饭团`
- 唤醒严格匹配：开启
- 唤醒别名：关闭
- 唤醒模糊匹配：关闭
- 唤醒阶段语音识别：腾讯云 STT
- 正式语音识别：腾讯云 STT
- 文明分析：DeepSeek
- 主流程语音播报：腾讯云 TTS
- 当前主流程音色：基础/精品音色安全档
  - `tts.voice_type: 101001`
  - `tts.sample_rate: 16000`
  - `tts.model_type: 1`
- 问候语播放方式：优先使用用户预录音
  - `greeting.use_prerecorded_audio: true`
  - `greeting.audio_path: assets/audio/greeting.wav`
- 屏幕显示方式：机器人动画界面
  - `display.engine: robot_animation`
- 唤醒后连续监听：开启
  - `post_wake_speech.continuous_session: true`
  - `post_wake_speech.timeout_seconds: 30`

补充说明：

- 腾讯云“大模型音色”已经验证可调用成功，但当前主流程按用户要求暂时回到基础/精品音色。
- 已验证可用的大模型音色测试配置示例：
  - `voice_type: 501004`
  - `sample_rate: 24000`
- 目前主流程仍优先使用 `101001 / 16000` 这一组更稳的参数。
- 2026-06-20 已修复 STT 唤醒误触发问题：树莓派旧配置曾把唤醒词读成 `????`，导致归一化后出现空字符串匹配任意文本。当前已同时修复配置与匹配器逻辑，并增加“归一化后为空时绝不命中”的保护。

## 5. 当前功能实现状态

### 5.1 已完成

- 腾讯云 STT 已接入项目。
- 腾讯云 STT 已用于正式语音识别。
- 腾讯云 STT 已用于当前树莓派真实唤醒链路。
- DeepSeek 文明分析已接入项目。
- 腾讯云 TTS 已接入项目。
- 腾讯云 TTS 已在树莓派最小测试中成功出音。
- 用户预录问候语已支持。
- 唤醒成功后可播放机器人动画。
- 唤醒后动画与问候语可并行触发。
- 唤醒后进入连续监听，不是只处理一轮就立即回待机。
- 唤醒阶段 STT 返回空文本时，不再直接打断主循环。

### 5.2 已验证

- 树莓派上腾讯云 TTS 最小测试成功。
- 树莓派上腾讯云 STT 最小测试成功。
- DeepSeek 返回 JSON 分析结果成功。
- 树莓派上已验证严格唤醒结果：
  - `饭团你好呀` 不会唤醒
  - `饭团饭团` 可以正常唤醒
- 树莓派主流程配置已切到：
  - `speech_to_text.provider: tencentcloud`
  - `llm.provider: deepseek`
  - `tts.provider: tencentcloud`

## 6. 当前推荐运行命令

### 6.1 主程序

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 python main.py --config config/config.yaml
```

### 6.2 腾讯云 TTS 最小测试

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/test_tencentcloud_tts.py --config config/config.yaml
```

### 6.3 腾讯云 STT 最小测试

```bash
cd ~/dirty_words
source ~/.venv312/bin/activate
python scripts/test_tencentcloud_stt.py --config config/config.yaml --countdown 5 --duration 4 --text "饭团饭团"
```

## 7. 离线唤醒路线的现状

- 项目保留了 `openWakeWord` 离线唤醒方案的代码和文档。
- 目标离线唤醒词仍然是：`饭团饭团`
- 但截至当前，树莓派“真实可运行”的主配置不是 `openWakeWord`，而是 `STT 唤醒`
- 原因是当前优先保证整机主流程可测、可跑、可稳定验证

后续如果要回到本地离线唤醒路线，需要继续完成：

- “饭团饭团”自定义唤醒模型整理与训练
- `openWakeWord` 模型文件部署
- 阈值、噪声抑制、VAD 等参数二次调优

## 8. 临时文件与清理规则

以下目录或文件容易在测试时快速增长，验证完成后应及时清理，且不要提交到 GitHub：

- `recordings/`
- `exports/`
- `tmp/`
- `training_data/`
- `assets/audio/` 中的临时测试音频
- 临时生成的日志文件
- 树莓派上的临时测试脚本

补充规则：

- `recordings/` 中的测试 WAV 不要长期堆积。
- `exports/` 和 `tmp/` 只作中转，不作正式资产。
- `config/config.yaml.backup_*` 属于本机备份，不提交。
- 训练样本、导出压缩包、真实录音都属于个人/设备数据，不提交。

## 9. 当前已知技术债

虽然 TTS 相关关键乱码已处理，但仓库里仍有一部分历史编码污染未完全清理，后续应统一修复。当前重点文件包括：

- `modules/app.py`
- `modules/llm/openai_civil_analyzer.py`
- `modules/speech_to_text/tencentcloud_stt.py`
- `modules/models.py`

这些文件里的中文日志、默认文案或提示词存在历史乱码风险。后续应统一改为干净 UTF-8 中文。

## 10. 当前推荐下一步

最推荐的下一步是做一次完整实机闭环验证：

1. 说“饭团饭团”完成唤醒
2. 观察机器人动画和问候语
3. 继续说一句需要分析的话
4. 检查腾讯云 STT 识别结果
5. 检查 DeepSeek 文明分析结果
6. 检查腾讯云 TTS 是否按预期播报

验证通过后，再继续做两件事：

- 统一修复剩余源码中的中文乱码
- 再根据体验决定是否重新推进本地离线唤醒路线
