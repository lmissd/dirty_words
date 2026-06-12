# 安全说明

## 敏感信息

不要提交以下内容：

- OpenAI API Key
- 树莓派登录密码
- WiFi 密码
- 真实儿童语音文件
- 任何个人隐私数据

## 已采取的仓库保护

以下文件默认被 Git 忽略：

- `.env`
- `config/config.yaml`
- `LOCAL_CREDENTIALS.md`
- `*.private.md`
- `recordings/*`
- `logs/*`

## 儿童语音数据

项目默认建议不长期保存录音。配置项 `privacy.keep_recordings` 默认为 `false`，处理完成后应删除临时音频。

如果未来需要保存音频用于调试，建议只在本地短期保存，并在提交前确认没有被 Git 跟踪。
