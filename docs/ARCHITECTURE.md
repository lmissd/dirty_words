# 架构说明

## 总体设计

文明用语机器人采用“主流程编排 + 功能模块接口”的结构。`main.py` 只负责启动应用，真正的业务流程由 `CivilLanguageRobotApp` 编排。

核心模块之间通过抽象接口通信，便于未来替换云服务、唤醒词引擎、显示界面或硬件设备。

## 状态机

```text
standby -> wakeword -> recording -> speech_to_text -> analysis -> display -> tts -> standby
```

任何阶段发生异常时，应用会记录日志、显示错误提示，并在短暂停顿后返回待机，避免进程直接崩溃。

## 模块职责

- `modules/wakeword`：唤醒词检测。当前提供控制台模拟实现，后续可扩展 Porcupine、离线关键词或麦克风阵列方案。
- `modules/recorder`：录音。当前提供基于 `sounddevice` 的 WAV 录音实现。
- `modules/speech_to_text`：语音转文字。当前提供 OpenAI Speech-to-Text 适配器。
- `modules/llm`：文明用语分析。当前提供 OpenAI GPT 和 DeepSeek JSON 分析适配器。
- `modules/tts`：文字转语音。当前提供 OpenAI TTS 适配器。
- `modules/display`：结果显示。当前提供控制台显示和 Tkinter 全屏显示。
- `modules/utils`：配置加载、日志、错误类型、音频播放和磁盘检查。

## 配置边界

所有可变参数都来自 `config/config.yaml` 或环境变量，代码中不硬编码真实 API Key、设备密码、模型名称或硬件参数。

公开仓库只提交 `config/config.example.yaml`。真实部署时复制为 `config/config.yaml` 并按设备情况修改。

## 扩展方式

新增能力时优先新增接口实现，不直接改动主流程。例如：

- 新增摄像头情绪识别：增加 `modules/vision/`，再在状态机中插入可选步骤。
- 替换语音识别供应商：新增 `speech_to_text` 实现，并通过配置选择。
- 新增远程管理后台：增加独立服务模块，不让主循环依赖具体 Web 框架。
