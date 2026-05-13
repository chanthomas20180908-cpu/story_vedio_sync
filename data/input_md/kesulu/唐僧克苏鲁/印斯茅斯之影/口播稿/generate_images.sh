python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格的心理恐怖插画：印斯茅斯01_唐僧看着手中的车票，感到恶心。",
  "style_guide": {
    "核心美学": "Same reference style: Dark comic, heavy ink, grotesque surrealism, hyper-detailed textures.",
    "视觉丰富度": "Extreme detail density, no empty space, abstract horror."
  },
  "角色状态_唐僧(Tang Seng)": {
    "形象": "保持参考图中的光头僧人形象，身披墨绿色僧袍。",
    "动作神态": "唐僧正对着镜头，一只手嫌弃地捏着一张腐烂、滴着黑色粘液的车票，仿佛那是世界上最脏的东西；另一只手捂住口鼻，眉头紧锁，眼神中充满‘这玩意儿真恶心’的审判感(Judgmental look)。"
  },
  "克苏鲁式抽象装饰(Cthulhu_Abstract)": {
    "元素堆砌": "车票周围环绕着苍蝇般的黑色微粒；背景是扭曲的售票窗口，窗口边缘长满了藤壶和海藻；空气中漂浮着绿色的毒气云雾，云雾中隐约浮现出死鱼的骨架；地面上渗出像石油一样的黑色液体。",
    "物理规则": "车票边缘在融化，滴落的液体在半空中变成微小的触手。"
  },
  "心理暗示符号(Psychological_Symbolism)": {
    "暗示内容": "背景中无数双浑浊的鱼眼在暗处窥视；头顶悬浮着巨大的生锈鱼钩（象征诱饵）；售票窗口呈现出鲨鱼张开大嘴的形状（象征吞噬）。"
  },
  "色彩与感官氛围(Atmosphere)": {
    "色调": "腐烂的黄绿色(Rotten Yellow-Green)与深海蓝(Deep Sea Blue)的病态对比。",
    "质感": "画面充满‘油腻’和‘腥臭’的视觉通感，仿佛能闻到死鱼的味道。"
  },
  "视觉构图(Composition)": {
    "镜头": "广角镜头，夸大唐僧手中的车票和他的厌恶表情，背景呈放射状扭曲。",
    "禁令": "严禁出现任何文字、数字、现代UI。"
  },
  "负面提示": ["text", "words", "subtitle", "alphabet", "English", "Chinese", "bright colors", "cute", "realistic train station", "clean paper"]
}
EOF
)"

python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格的心理恐怖插画：印斯茅斯02_唐僧在充满鱼腥味的公交车上，司机极其怪异。",
  "style_guide": {
    "核心美学": "Same reference style: Dark comic, heavy ink, grotesque surrealism, hyper-detailed textures.",
    "视觉丰富度": "Extreme detail density, no empty space, abstract horror."
  },
  "角色状态_唐僧(Tang Seng)": {
    "形象": "保持参考图中的光头僧人形象，身披墨绿色僧袍。",
    "动作神态": "唐僧缩在公交车座位角落，脸色苍白，强忍呕吐感，眼神惊恐地斜视前方；双手紧紧抓住扶手，仿佛那是救命稻草。"
  },
  "克苏鲁式抽象装饰(Cthulhu_Abstract)": {
    "元素堆砌": "公交车内部布满了潮湿的青苔和贝壳；扶手变成了滑腻的触手；车窗外不是风景，而是深海的黑暗漩涡；司机的背影极其宽大，脖子上层层叠叠的褶皱像鱼鳃一样张开，周围环绕着水母般的发光浮游生物。",
    "物理规则": "车厢空间在视觉上被拉长，呈现出幽闭恐惧症般的压迫感。"
  },
  "心理暗示符号(Psychological_Symbolism)": {
    "暗示内容": "座位上的花纹由无数只死鱼的眼睛组成；车顶悬挂着类似捕鱼网的黑色丝状物，网中似乎兜着模糊的人脸（象征被捕获的命运）；司机的后视镜中倒映出的不是唐僧，而是一个骷髅（象征死亡预警）。"
  },
  "色彩与感官氛围(Atmosphere)": {
    "色调": "阴冷的灰蓝色(Cold Grey-Blue)与血腥红(Bloody Red)的点缀。",
    "质感": "强调‘潮湿’与‘窒息’感，空气中仿佛充满了水汽和海腥味。"
  },
  "视觉构图(Composition)": {
    "镜头": "过肩镜头，从唐僧的后方看向怪异的司机，强调被困的无助感。",
    "禁令": "严禁出现任何文字、路牌、现代车辆仪表盘。"
  },
  "负面提示": ["text", "words", "subtitle", "alphabet", "English", "Chinese", "bright colors", "cute", "normal bus", "sunny outside"]
}
EOF
)"

python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格的心理恐怖插画：印斯茅斯03_疯老头扎多克向唐僧透露恐怖真相。",
  "style_guide": {
    "核心美学": "Same reference style: Dark comic, heavy ink, grotesque surrealism, hyper-detailed textures.",
    "视觉丰富度": "Extreme detail density, no empty space, abstract horror."
  },
  "角色状态_唐僧(Tang Seng)": {
    "形象": "保持参考图中的光头僧人形象，身披墨绿色僧袍。",
    "动作神态": "唐僧被一个看不清面容的疯老头紧紧抓住手臂，满脸惊恐和厌恶，身体后仰试图挣脱；眼神中流露出‘这人疯了’的恐惧。"
  },
  "克苏鲁式抽象装饰(Cthulhu_Abstract)": {
    "元素堆砌": "疯老头的身体正在半透明化，体内可见鱼骨结构；周围环境是破败的码头，木板缝隙中伸出无数只苍白的小手；天空中乌云密布，云层形状像是一张巨大的、垂涎欲滴的嘴；空气中充满了破碎的金色几何碎片（象征邪恶的金子）。",
    "物理规则": "老头的影子投射在墙上，却呈现出巨大的深潜者怪物轮廓。"
  },
  "心理暗示符号(Psychological_Symbolism)": {
    "暗示内容": "唐僧周围环绕着螺旋状的DNA链条，但链条正在断裂和变异（象征人种退化）；背景海面下隐约可见巨大的城市废墟倒影（象征水下文明）；酒瓶倒在地上，流出的不是酒，而是鲜血。"
  },
  "色彩与感官氛围(Atmosphere)": {
    "色调": "绝望的铁锈红(Rusty Red)与深渊黑(Abyss Black)。",
    "质感": "强调‘疯狂’与‘混乱’，画面线条带有强烈的震颤感，仿佛在尖叫。"
  },
  "视觉构图(Composition)": {
    "镜头": "低角度仰视，突出疯老头疯狂的压迫感，背景是大海和天空的压抑交界线。",
    "禁令": "严禁出现任何文字、对话框、现代建筑。"
  },
  "负面提示": ["text", "words", "subtitle", "alphabet", "English", "Chinese", "bright colors", "cute", "normal old man", "peaceful sea"]
}
EOF
)"

python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格的心理恐怖插画：印斯茅斯04_唐僧在旅馆房间内抵挡门外的怪物。",
  "style_guide": {
    "核心美学": "Same reference style: Dark comic, heavy ink, grotesque surrealism, hyper-detailed textures.",
    "视觉丰富度": "Extreme detail density, no empty space, abstract horror."
  },
  "角色状态_唐僧(Tang Seng)": {
    "形象": "保持参考图中的光头僧人形象，身披墨绿色僧袍。",
    "动作神态": "唐僧满头大汗，五官因为极度用力而扭曲，正死命地用身体顶住一扇摇摇欲坠的木门；眼神疯狂地看向旁边敞开的窗户，寻找生路。"
  },
  "克苏鲁式抽象装饰(Cthulhu_Abstract)": {
    "元素堆砌": "木门已经变形，门缝中挤出绿色的粘液和像海葵一样的触须；房间内的家具（床、椅子）都变成了长满牙齿的生物，正在尖叫；墙纸剥落，露出后面像内脏一样的蠕动墙壁；天花板上垂下无数钓鱼线，末端挂着眼球。",
    "物理规则": "房间的空间正在被外部力量挤压，直线变得弯曲，仿佛整个房间在呼吸。"
  },
  "心理暗示符号(Psychological_Symbolism)": {
    "暗示内容": "门上隐约浮现出无数只湿漉漉的手印（象征群体的围攻）；窗户外的月亮是一只巨大的爬虫类眼睛（象征无处可逃的监视）；地面上的影子呈现出紧箍咒的形状，束缚着唐僧的双脚。"
  },
  "色彩与感官氛围(Atmosphere)": {
    "色调": "幽闭的霉绿色(Moldy Green)与警示黄(Warning Yellow)。",
    "质感": "强调‘紧迫’与‘崩溃’，光影对比极其强烈，仿佛心跳般闪烁。"
  },
  "视觉构图(Composition)": {
    "镜头": "倾斜构图（Dutch Angle），增加不稳定性与紧张感，焦点在唐僧顶门的动作和门缝中渗出的恐怖。",
    "禁令": "严禁出现任何文字、现代门锁、清晰的怪物全貌（只展示局部）。"
  },
  "负面提示": ["text", "words", "subtitle", "alphabet", "English", "Chinese", "bright colors", "cute", "safe room", "open door"]
}
EOF
)"

python3 /Users/test/code/Python/AI_vedio_demo/pythonProject/debug/nanobanana/run_gemini_flash_generate.py \
  --aspect-ratio "9:16" \
  --image '/Users/test/Library/Mobile Documents/com~apple~CloudDocs/BEAST_BEING/my_mutimedia/my_scripts/唐僧克苏鲁/大衮/大衮3/原图/download (30).png' \
  "$(cat <<'EOF'
{
  "任务": "生成克苏鲁风格的心理恐怖插画：印斯茅斯05_唐僧在草丛中发现深潜者真相。",
  "style_guide": {
    "核心美学": "Same reference style: Dark comic, heavy ink, grotesque surrealism, hyper-detailed textures.",
    "视觉丰富度": "Extreme detail density, no empty space, abstract horror."
  },
  "角色状态_唐僧(Tang Seng)": {
    "形象": "保持参考图中的光头僧人形象，身披墨绿色僧袍。",
    "动作神态": "唐僧趴在茂密的、带刺的草丛中，浑身泥泞，一只手捂住嘴巴，瞳孔放大到极致，透过草丛缝隙死死盯着前方，极度恐惧。"
  },
  "克苏鲁式抽象装饰(Cthulhu_Abstract)": {
    "元素堆砌": "草丛的每一片叶子都长着细小的牙齿；前方站立的巨大黑影呈现出半人半蛙的轮廓，背部生有巨大的背鳍，皮肤覆盖着湿滑的鳞片；黑影周围环绕着鬼火般的蓝绿色光芒；天空中悬浮着巨大的、破碎的镜子碎片，映照出唐僧自己也在发生变异（耳朵变尖）。",
    "物理规则": "月光如液体般流淌，将一切笼罩在不真实的扭曲光影中。"
  },
  "心理暗示符号(Psychological_Symbolism)": {
    "暗示内容": "深潜者手中的三叉戟由无数根人类腿骨组成（象征牺牲者）；唐僧身下的泥土中伸出无数只手试图将他拉入地下（象征血脉的召唤）；背景远处是大海，海面上形成了一个巨大的漩涡，中心通向地狱。"
  },
  "色彩与感官氛围(Atmosphere)": {
    "色调": "神秘的月光银(Moonlight Silver)与深海青(Deep Ocean Cyan)。",
    "质感": "强调‘冰冷’与‘真相大白’的战栗感，画面带有冷冻般的结晶质感。"
  },
  "视觉构图(Composition)": {
    "镜头": "主观视点（POV），透过草丛缝隙看巨人，强调偷窥的压迫感和被发现的恐惧。",
    "禁令": "严禁出现任何文字、清晰的人类面孔（除了唐僧）、白天场景。"
  },
  "负面提示": ["text", "words", "subtitle", "alphabet", "English", "Chinese", "bright colors", "cute", "normal grass", "friendly monster"]
}
EOF
)"
