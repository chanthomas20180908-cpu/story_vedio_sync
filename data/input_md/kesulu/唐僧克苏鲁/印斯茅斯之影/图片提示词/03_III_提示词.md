# 印斯茅斯 03 章 · 图片生成脚本（疯老头&活祭真相）

# 图1：码头一角，唐僧与疯老头初遇
python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格插画：破败码头边，唐僧被疯老头招手拦住。",
  "style_guide": {
    "核心美学": "Grimy dock horror, character-driven scene.",
    "视觉丰富度": "码头、海面和人物表情细节都很丰富。"
  },
  "角色状态_唐僧": {
    "形象": "光头、墨绿僧袍。",
    "动作神态": "唐僧一只脚还在前进姿势，身体微微后仰被拦住，表情“这老头不对劲”，一手本能护住自己怀里的包袱。"
  },
  "疯老头扎多克": {
    "外观": "瘦高、背微驼、满脸皱纹和乱胡子，穿着破旧外套；眼睛浑浊但极度兴奋。",
    "动作神态": "伸长一只瘦骨嶙峋的手抓住唐僧袖子，另一只手拿着半空的酒瓶疯狂比划。"
  },
  "环境与抽象装饰": {
    "元素": "木板码头裂开，缝隙中能看到下面黑水中游动的巨大影子；柱子上缠满海藻和破渔网；远处破败的仓库像张开嘴的巨兽。"
  },
  "心理暗示符号": {
    "内容": "唐僧和老头脚下影子组合起来像一只巨大的触手；酒瓶里剩下的液体颜色诡异，里面隐约有小鱼形轮廓在动。"
  },
  "氛围": {
    "色调": "铁锈红 + 暗褐 + 冷蓝海面。",
    "质感": "强调潮湿、霉味和酒精味混杂的脏乱感。"
  },
  "构图": {
    "镜头": "中景纵向构图，下方是破木板与黑水，上方是两人交互，背景是废仓库。",
    "禁令": "无现代标语、无干净整齐码头。"
  },
  "负面提示": ["clean dock", "modern crane", "text", "cheerful fisherman"]
}
EOF
)"

# 图2：岛上邪教仪式想象画面（老头讲述）
python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格插画：疯老头口中的南海小岛献祭场景，以幻象方式呈现在唐僧身后。",
  "style_guide": {
    "核心美学": "Mythic ritual scene, high density, sacrificial horror.",
    "视觉丰富度": "岛屿、石像、祭坛和海底怪物元素堆满画面。"
  },
  "角色状态_唐僧_前景": {
    "形象": "唐僧坐在码头石块上，背对观众、略偏侧面。",
    "动作神态": "一手扶额，一手托腮，明显被吓到但又不得不听完的表情。"
  },
  "幻象场景_背景": {
    "岛屿": "火山岛形状，岸边是黑沙滩，中央高地上有环形石阵和巨型半鱼半蛙石像。",
    "祭坛": "石坛上绑着人形祭品，周围土著在火光中起舞，动作夸张扭曲。",
    "海怪": "海面涌起巨大黑影，伸出几条黏滑触手搭在岩石上，触手上布满吸盘和眼睛。"
  },
  "克苏鲁抽象装饰": {
    "元素": "天空卷着不自然的星辰排列成未知星座；石像表面刻满螺旋和眼睛符文；火堆烟雾中漂浮出类似深潜者的模糊轮廓。"
  },
  "心理暗示符号": {
    "内容": "岛的轮廓整体像一只张嘴怪鱼，祭坛在咽喉位置；祭品手脚伸展方向对应某种神秘星座构图。"
  },
  "氛围": {
    "色调": "火光橙红 + 深海墨绿 + 黑灰石色。",
    "质感": "强调炎热、血腥与潮湿海风同时存在的矛盾。"
  },
  "构图": {
    "镜头": "下方小比例唐僧前景，上方大面积是类似壁画/幻觉的岛屿仪式画面。",
    "禁令": "无现代宗教符号、无文字。"
  },
  "负面提示": ["church cross", "text", "neon", "modern city"]
}
EOF
)"

# 图3：DNA/血统变异的抽象意象
python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格抽象插画：表现“人类与海底怪物混血，长大后变成鱼”的血统恐怖。",
  "style_guide": {
    "核心美学": "Abstract body horror, DNA symbolism, transformation.",
    "视觉丰富度": "充满细节的螺旋、骨骼、鱼鳞纹理。"
  },
  "角色剪影": {
    "形象": "多个人类剪影从下往上排成一列，从正常人形逐渐变成鱼人轮廓。",
    "状态": "越往上越接近深潜者形态，最后一层彻底变成下水的黑色鱼影。"
  },
  "克苏鲁抽象装饰": {
    "元素": "中央一根巨大的螺旋 DNA 链，一半是人类骨骼结构，另一半是鱼骨和触手；链条周围悬浮着无数眼睛和牙齿碎片；背景是海底城市轮廓。"
  },
  "心理暗示符号": {
    "内容": "螺旋链条末端插入一座小镇轮廓模型（暗示印斯茅斯）；底部的人类剪影脚下是墓碑形石块，上面没有字，只刻着鱼形符号。"
  },
  "氛围": {
    "色调": "冷青绿 + 骨白 + 深蓝。",
    "质感": "整体偏冰冷、医学解剖感与邪教感叠加。"
  },
  "构图": {
    "镜头": "竖版中心是巨大 DNA 螺旋，人类/鱼人剪影沿两侧或一侧垂直排列。",
    "禁令": "无字母、无真实基因文字标签。"
  },
  "负面提示": ["ATCG letters", "text", "lab UI", "scientist"]
}
EOF
)"

# 图4：疯老头歇斯底里指向海面
python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格插画：疯老头突然歇斯底里，指向远处海面，唐僧被吓得半跪在地。",
  "style_guide": {
    "核心美学": "Dynamic character acting, shore-side panic.",
    "视觉丰富度": "人物表情、海浪、水面阴影都很丰富。"
  },
  "角色状态_唐僧": {
    "形象": "同一 IP。",
    "动作神态": "唐僧一只手撑着湿滑的石块，半跪半坐，另一只手护住头，表情震惊、瞳孔放大，朝老头所指方向看去。"
  },
  "疯老头": {
    "动作神态": "站在更前方，双臂张开，一只手指向海面，嘴大张仰天尖叫，胡子和头发被海风吹乱，看起来完全失控。"
  },
  "克苏鲁抽象装饰": {
    "海面": "远处海面本身看似平静，但浪尖有不自然的黑色纹路像巨大轮廓在水下滑动；近处浪花飞溅呈触手形状。",
    "岸边": "岩石上满是潮湿海藻，海藻像手指一样攀附。"
  },
  "心理暗示符号": {
    "内容": "老头影子在岩石上拉长成深潜者形态；唐僧影子则被浪花切断成几段，暗示命运被撕裂。"
  },
  "氛围": {
    "色调": "深蓝灰 + 冷白浪花高对比。",
    "质感": "强调风声、浪声与尖叫几乎能从画面中听到。"
  },
  "构图": {
    "镜头": "略低角度仰视，两人占下半部，海与天占上半部，老头手指方向引导视线到海面阴影。",
    "禁令": "无船只、无灯塔光束。"
  },
  "负面提示": ["ship", "lighthouse beam", "calm tourists", "text"]
}
EOF
)"

# 图5：疯老头被“拉走”（不见真凶）
python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格插画：疯老头跑进狭窄巷子深处，巷子尽头有看不见真身的黑暗在拉扯他，只留下一声惨叫。",
  "style_guide": {
    "核心美学": "Narrow alley, unseen threat, strong motion.",
    "视觉丰富度": "巷子墙面、垃圾、水渍和阴影都极细致。"
  },
  "角色状态": {
    "疯老头": "在巷子中段，被向后猛拽，身体后仰、脚离地，一只手抓住墙面砖缝，指甲掐进缝里。",
    "唐僧": "只在巷口出现一个小剪影，站在光亮处，不敢再往前一步。"
  },
  "克苏鲁抽象装饰": {
    "元素": "巷子深处不是单纯黑暗，而是蠕动着的深色雾团与触须轮廓；墙面的霉斑和裂痕排列成巨大张嘴脸；地面水坑中倒映出完全不同的场景——海底城市和无数鱼人抬头。"
  },
  "心理暗示符号": {
    "内容": "老头被拉扯方向与巷子透视方向相反，制造违和感；巷口唐僧影子被巷子直角切成两半，象征“知道太多就会被切断”。"
  },
  "氛围": {
    "色调": "近巷口略暖灰，越往里越冷蓝黑。",
    "质感": "强调湿冷、霉味和一种喉咙发紧的压迫。"
  },
  "构图": {
    "镜头": "纵深极强的竖版巷道构图，巷口小亮口、唐僧在下方，老头在中段被拉向上方深处黑暗。",
    "禁令": "无现代路灯、招牌文字。"
  },
  "负面提示": ["street lamp", "shop sign text", "busy alley", "cute"]
}
EOF
)"
