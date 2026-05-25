# 上下文交接文档

> 供新 Agent 快速恢复当前进度，继续迭代，无需重新收集信息。
> 最后更新：2026-05-22

---

## 一、项目定位

**项目目录**：`/Users/test/code/Python/AI_vedio_demo/story_vedio_sync`

端到端 AI 视频生成系统：
- 输入：故事脚本（Markdown）
- 流程：LLM 生成口播稿 -> TTS（DashScope）-> 字幕对齐 -> AI 分镜生图（Gemini/cloubic）-> 视频合成
- UI：Gradio Web 界面
- 另有 `story_remix` 模块：多故事混搭生成新故事

代码架构文档：`docs/story_remix_architecture.md`

---

## 二、硬约束

- **绝对禁止任何 Git 操作**：不能运行任何包含 `git` 的命令。
- 查询/检索可自动执行。
- 写操作/外部效果动作：先给方案，再用三行预告，等用户确认后执行。
- 输出要短、结论先行、暴露核心假设。

---

## 三、账号事实与历史判断

账号数据来自 2026-05-14 抖音后台截图：

| 指标 | 数值 |
|---|---|
| 粉丝 | 约 153 |
| 总作品 | 92 个 |
| 2 秒完播率 | 40-48% |
| 全程完播率 | 约 0%（极少数 <1%） |
| 平均观看时长 | 3-12 秒 |
| 每集涨粉 | 0 |
| 推荐页流量 | 约 92% |
| 受众 | 90% 男性，24-35 岁为主 |

历史判断：
- 旧内容不是完全没有钩子，而是 2 秒后到 30 秒之间松弛。
- 旧生产形态是“静图 + 旁白 + 字幕”的 PPT 式视频，已不能满足目标。
- 用户明确追求“有意思、拿得出手、惊艳的 AI 视频成果”，不是继续堆普通脚本。

---

## 四、当前主线

当前主线已经从“黑暗狂魔系列继续生产”切换为：

**《女儿国旧日神事件》AI 动画短片样片**

核心定位：
- 混搭：西游记女儿国 x 旧日神污染 x 异常档案 x 生物寄生
- 画风：`天书奇谭` 式中国经典动画，水墨设色、纸纹、赛璐璐人物、邮票式设定板
- 目标：从 PPT 式视频升级为真正的 AI 动画短片
- 首个强钩子：`取经队进入女儿国后，只有猪八戒的影子逃了出来。`

核心故事：
- 唐僧在女儿国念错一页经。
- 子母河不是普通河水，而是同源寄生介质。
- 女儿国不是艳遇劫，而是古老孵化器。
- 子母河负责播种，经书负责唤醒，取经人负责把胚胎带去西天。

---

## 五、已完成资产

### 方案文档

- `docs/main_account_content_strategy_v1.md`：主账号内容战略 1.0
- `docs/video_episode_001_deep_sea_relic_pack.md`：废寺深海遗骨生产包，后续优先级已降低
- `docs/video_episode_002_womankingdom_cthulhu_pack.md`：女儿国旧日神事件生产包
- `docs/womankingdom_cthulhu_video_plan.html`：当前阶段 HTML 方案快照
- `docs/womankingdom_cthulhu_handoff.md`：女儿国项目专用交接文档

### 视觉资产

目录：`data/Data_results/picture_results/video_episode_002_womankingdom_cthulhu_v1/`

参考资产：
- `references/visual_board_tianshu_style.png`：主设定图，确立老动画水墨风格
- `references/character_turnaround_sheet.png`：角色多角度定稿图，后续生成必须优先参考
- `references/shot_tangseng_wrong_scripture_v0.png`：早版唐僧念错经画面

关键帧：
- `keyframes/shot_01_bajie_shadow_escape.png`
- `keyframes/shot_02_tangseng_wrong_scripture.png`
- `keyframes/shot_03_zimu_river_black_sea.png`

小样：
- `womankingdom_6s_style_sample.mp4`：6 秒无内嵌字幕节奏小样
- `womankingdom_6s_style_sample.srt`：对应字幕

注意：本机 `ffmpeg` 没有 `drawtext` 滤镜，内嵌字幕失败；已输出 `.srt`，可导入剪映/PR。

---

## 六、已验证结论

成立：
- `天书奇谭` 式老动画画风是强差异化资产。
- “西游经典场景被旧日神污染”的混搭识别度强。
- “八戒影子逃逸”是当前最强视觉钩子。
- 角色定稿图 -> 关键帧 -> 本地轻动效 -> SRT 的基础链路可跑通。

未成立：
- 6 秒小样只是节奏预览，不是惊艳视频。
- 静图推拉仍然接近 PPT。
- 下一步必须用图生视频模型测试真实动态。

---

## 七、下一步优先级

### 1. Seedance 2.0 动态镜头测试

优先镜头：`八戒影子逃逸`

目标效果：
- 黑影像墨一样在地面爬动。
- 影子边缘长出细小触手。
- 远处唐僧和悟空保持角色一致，不乱变形。
- 保留 `天书奇谭` 式纸纹、水墨、赛璐璐画风。

建议输入：
- 角色定稿图：`references/character_turnaround_sheet.png`
- 关键帧：`keyframes/shot_01_bajie_shadow_escape.png`
- 风格参考：`references/visual_board_tianshu_style.png`

### 2. 20 秒概念预告

镜头结构：
1. 八戒影子从地面爬出来，2-3 秒
2. 唐僧翻开经书，经文变黑墨触手，4-5 秒
3. 子母河水面翻成黑色海底，5 秒
4. 女王腹部胎光脉冲，宫女影子合并，5 秒
5. 黑场标题：`别去西天。那里只是另一个子宫。`，2 秒

### 3. 完整短片

只有 20 秒概念预告成立后，再扩展到 45-60 秒完整短片。

---

## 八、模型判断

当前排序：
1. **Seedance 2.0**：优先测试。目标是惊艳级图生视频和多参考图保持。
2. **Runway Gen-4 Turbo**：备选，接入清晰，适合作对照。
3. **Veo 3.1 Fast / Veo 3.1**：备选，质量强，但可能把老动画风格拉向写实电影感。
4. **Sora**：暂不作为生产核心。

---

## 九、给新 Agent 的执行建议

- 不要回到普通“脚本 + 静图 + TTS”路径。
- 不要继续优化废寺遗骨方向，当前更强方向是女儿国旧日神事件。
- 不要让模型自由发挥角色形象；先参考角色定稿图。
- 生图/视频里尽量不让模型生成中文正文，中文标题和字幕后期叠加。
- 所有写操作前遵守三行预告并等待用户确认。
- 不要执行任何 Git 操作。
