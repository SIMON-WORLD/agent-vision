---
name: free-vision-bridge
description: 当主模型不支持图像输入，而用户要求查看、读取、描述或分析图片/截图时使用。调用 vision_bridge.py see 把图片交给免费视觉模型（默认智谱 glm-4v-flash），并把识别结果作为回答依据。
---

# Free Vision Bridge

## 何时使用

- 用户给出图片路径并要求“看一下 / 描述 / 分析 / 识别 / OCR”；
- 用户粘贴了截图但主模型收到的是不支持格式或无法读取的图片；
- 需要从截图提取报错、UI 元素、图表数据或文字。

## 工作流程

1. 确认图片路径真实存在，支持 png / jpg / jpeg / webp / gif / bmp。
2. 若本任务目录已配置 `.env`，直接运行：

   ```bash
   python vision_bridge.py see <图片路径> -q "<用户的具体问题>"
   ```

3. 若未配置 `.env`，显式传入环境变量：

   ```bash
   VISION_API_KEY=<key> VISION_BASE_URL=<url> VISION_MODEL=<model> \
     python vision_bridge.py see <图片路径> -q "<问题>"
   ```

4. 把脚本输出作为事实依据，用中文向用户转述；后续追问基于识别文本继续处理。
5. 如果本地代理正在运行（`proxy` 模式），粘贴图片会自动转成文字描述，不需要手动执行脚本；此时不要在回复里声称“直接看到图片”。

## 注意事项

- 图片只会发送到配置的视觉服务商（默认智谱）。敏感截图先与用户确认。
- 识别结果来自第三方视觉模型，可能存在细节偏差；重要数字、密钥类内容要提示用户核对。
- 不要把 `.env` 提交到 Git 或分享给他人。
