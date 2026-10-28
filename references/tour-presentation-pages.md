# 全屋参观审核呈现 SOP

本文件是审核呈现的唯一规范。契约标识：`three-stage-presentation/2`。
共享入口为 `scripts/production/tour_pages.py`，模板与交互位于 `assets/h5/tour/`。
只更换案例数据和素材，不在案例目录另写页面外壳；诊断工具不能替代正式审核。

## 1. 固定三步

| 步骤 | 页面与版式 | 审核及推进条件 |
|---|---|---|
| 路线与镜头 | `route.html` / `index.html`。左侧完整二维户型、连续路径、当前机位及朝向；右侧开始、房间节点、结束及全片时间点；下方播放、倍速、重播、拖动 | 先确认顺序、路线、朝向和节奏，并通过单独三维检查链接审阅实际镜头，再进入视频制作。页面没有视频、不显示“三维预演”按钮；样例不显示“样例预览”胶囊 |
| 视频审阅 | `video.html`。左侧16:9视频；右侧统一“参观路线”面板，默认路线图，可切换逐行房间列表 | 审核实际构图、运镜、转场、遮挡和重复，再制作讲解成片。视频未绑定时显示待生成，不用实时三维替代 |
| 讲解成片 | `narrated.html`。沿用视频审阅版式，视频下方只放讲解、音乐、字幕开关与折叠文稿 | 审核声画同步和整体体验。声音未绑定时显示待生成；准备过配音不等于已有成片 |

三个页签固定在顶部横向排列，顺序、名称不变。窄屏横向滚动页签，内容上下排列；
不用侧边导航，不强行让视频与右侧面板等高。使用暖白/米色、紧凑控件，不混入覆盖报告、
对象ID、累计转角、调试卡或内部解释。

### 制作顺序与执行关卡

三个页签代表三个独立制作阶段，不能一次连续生成第二、第三步。

1. 路线确认后，沿用 `route_rehearsal.require_route` / `preview_gate` 才能捕获视频。允许审阅捕获的例外授权只允许产出待审视频，不等于视频审阅通过。
2. 视频编码、时间轴检查和 `tour-pages` 打包结束后，停在视频审阅。页面同时生成 `video-review.pending.json`，所有确认项默认 false，不自动批准、不自动开始配音。
3. 用户完整审阅具体视频并明确同意后，依据真实对话填写独立确认记录：`homeowner-video-approval/1`，status=approved，approvalSource=explicit_user_confirmation，confirmedBy/evidence 非空，四项检查全部 true。视频及 tour 均以文件路径和 SHA-256 绑定。测试、工程通过、路线批准、审阅捕获授权均不能代替该确认。
4. 调用 `narration-prepare`，验证确认记录和源视频后才可进入配音生成、字幕对齐和音乐准备。此命令只输出授权收据与空音频占位的合成任务，不调用 TTS、不自动使用已有声音。外部本地模型也必须在这一步成功后调用，不得用案例脚本串行跳过视频审阅。
5. `narration-compose` 在混音/写字幕/合成前再次验证确认与所有文件哈希；输入已对齐、已调好音量的 voice 和可选 music，保留视频编码帧，生成 AAC 音轨、短句可选字幕及 SRT。字幕不是烧录字幕，声音质量与最终声画同步仍待第三步审阅。合成结果不自动验收。合成报告同时保存选定配音/音乐哈希、原始字幕区间、短句字幕、规范化任务、FFmpeg版本/参数、生成器哈希及输入输出时间轴；只保存选定音轨引用，不复制私有声纹参考。
6. 生产 `tour-pages` 包装讲解页也需要同一 `videoReview`，已有音频不能绕过关卡。视频或路线变更后旧确认失效，重新停回视频审阅；只调整讲解仍须重新审阅第三步。

共享命令（均使用新输出目录）：

```text
python scripts/production/h5.py narration-prepare --job NARRATION_JOB --out NEW_PREPARATION
python scripts/production/h5.py narration-compose --job ALIGNED_AUDIO_JOB --out NEW_COMPOSITION --ffmpeg EXISTING_FFMPEG
```

任务格式见 `assets/h5/tour/narration-job-template.json`。`videoReview` 为确认记录自身的 path/sha256 引用。
不要预填真实用户批准。`sample:true` 仅用于历史素材的页面演示，可展示完整三页，但确认模板标记 sample；不能授权准备或合成，也不代表当前方案批准。样例素材不能通过改标签冒充实际用户确认。
这些是共享命令与执行流程的约束，不能拦截用户在技能外手动调用任意外部工具；不得声称已控制所有第三方 TTS。

## 2. 统一交互

- 视频保持16:9与完整画面，不为了列对齐拉伸为方形或裁切。路线侧栏独立高度，桌面至少约300px宽。
- 侧栏为“路线图 / 房间列表”两个页签。地图显示完整轨迹、已走/未走、当前机位与独立朝向。
- 列表按开始、各房间、结束从上到下一行一个，名称左、时间右，当前节点高亮。清除“· 观看”等后缀，相邻同名节点只显示一次；底层章节及时间轴不改写。
- 切换图表不跳转、不暂停、不重播；点击列表节点才跳到该时间。播放、暂停、拖动、结束与回拖均依同一视频时间轴更新地图和高亮。
- 不再显示放大按钮、放大弹窗或视频下方重复章节。列表超出面板时只在列表内部滚动。
- 支持页签方向键、Home/End与键盘焦点。窄屏仍保留相同两页签，侧栏位于视频及讲解控件之后。
- 讲解、音乐、字幕独立开关，文稿折叠；页面切换时不自动播放声音。

## 3. 字幕规则

字幕按语义停顿组成短句，默认目标每组不超过14字，避免不足0.7秒的闪切；极短原始区间不得擅自扩展或覆盖下一段。
去除句末及停顿标点，保留数字小数与比例；整组直接替换，不逐字打字、不跳动。
白字细描边置于画面下部安全区域，不加大块黑底；相同字幕不重复刷新DOM。
原始文稿、声音与配音区间保留。没有逐字时间证据时，只在原区间内按字数分配短句时间，
数据注明 `estimated-within-source-intervals`，不能声称精确逐字对齐或平台强制规范。
字幕同步视频帧、跳转和开关；文稿不因屏幕字幕精简而丢失原文。

## 4. 辅助检查工具的边界

`camera-preview.html` 通过专用链接独立打开，提供返回路线页的链接。
只嵌入 `route-embed.html`（单个SVG、无导航及独立控制）与真实renderer，共用时间轴。
禁止嵌入带三个页签的完整审核页。`revision-review/index.html` 只用于前后修改对照，
不能代替三阶段审核。截图、功能检查、数值/网格检查与用户全片观感验收分别记录。

## 5. 数据、生成与回退

- 以同一冻结预演的tour/config/plan/timing/bundle哈希和明确毫米bounds生成，不复用别的案例的房间、路径、时间或声音。
- 视频必须声明SHA-256及对应tourSha256；用已有ffprobe核对完整帧数、帧率、时长。异路线、片段或重定时媒体不能套用旧路线。
- 讲解绑定确切videoSha256，音频分别校验哈希；外置配音接无原声视频，避免叠音。只复制指定成品音频，不扫描或暴露原始声纹参考与私有录音。
- 标准路线必须连续，cutBefore或超步速跳点拒绝包装成完整行走路线。
- `tour-pages.json` 记录presentationPolicy、输入、模板、资源和阶段状态，不授予批准。规则及源码指纹变化后原批准不自动沿用。
- 生成时执行 `validate_presentation`：顶层且唯一的三阶段导航、播放器状态、单一图/列表侧栏、章节归属、无重复章节/弹窗、无嵌套完整审核页。错误报错，不静默改成其它版式。
- 模块URL绑定内容哈希，包含依赖，防止新HTML配旧脚本。HTML/CSS及交互文件均进入指纹与输出身份记录。
- 使用新目录生成，原文件不覆盖；切换当前入口时保留旧目标与回退记录。HTTP服务须支持Range。无服务器保存、后台任务或自动发布。

正式命令：

```text
python scripts/production/h5.py plan-tour --job JOB --out NEWDIR
python scripts/production/h5.py tour-pages --rehearsal REHEARSAL_JSON --out NEWDIR
python scripts/production/h5.py tour-pages --rehearsal REHEARSAL_JSON --out NEWDIR --job PAGES_JOB --ffprobe EXISTING_FFPROBE
```

presentation job参考 `assets/h5/tour/presentation-job-template.json`，只绑定已有媒体，不调用生成服务。
`h5.py run --animation ...` 在批准、捕获及编码检查后调用同一页面生成器。直接捕获器只产帧，编码后也须走该入口。

## 6. 规则—实现—验收清单

下表表示能力已接入及验收方法，不把某一次案例的测试数量或观看结论当作未来案例通过。

| 通用规则 | 原生实现 | 回归与最终页面验收 |
|---|---|---|
| 视频确认后才能讲解 | tour_stage_gate.py、h5.py narration-prepare/compose、tour_pages.py | test_tour_stage_gate.py：待审/错误哈希/样例/审阅授权拒绝，真实短素材合成；测试批准仅为合成夹具 |
| 三阶段状态与固定外壳 | tour_pages.py、stage-template.html、rehearsal-template.html | test_tour_pages.py：无媒体/有视频/有讲解、错误嵌套反例；实际切换三个顶部页签 |
| 路线页简洁 | rehearsal-template.html、validate_presentation | 开始/结束、节点跳转、无视频/iframe/辅助入口；样例无状态胶囊 |
| 16:9及独立高度 | stage-theme.css | 实测播放器宽高比，窄屏布局，不能只核对CSS字符串 |
| 单一地图/列表面板 | route-panel.js、tour-media.js | test_tour_route_panel.mjs；切换前后时间及播放状态相同；每房间一行 |
| 清洁章节及跳转高亮 | chapter_nodes、tour-map.js、tour-media.js | test_tour_pages.py、test_tour_presentation.mjs；实际节点跳转与地图帧/位置一致 |
| 短句字幕与原文保留 | tour_subtitles.py、tour-media.js、stage-theme.css | test_tour_subtitles.py：标点、数字、短时段、原文、区间；实际字幕、开关与文稿 |
| 配音与音乐控制 | tour_pages.py、tour-media.js | 媒体哈希与边界反例；实际控件开关；不将控件检查当成音质验收 |
| 同源素材绑定 | tour_pages.py、tour-map.js | 异路线、帧数/时长/哈希错误拒绝；新户型bounds与fps独立 |
| 结构生成校验 | validate_presentation | 故意损坏产物：侧边导航、章节点移出面板、缺失侧栏、嵌套完整页应被拒绝 |
| 资源缓存稳定性 | tour_pages.py资源URL与manifest | 内容哈希查询串及依赖绑定测试；实际新生成页面无旧脚本报错 |
| 可复用真实页面验收 | scripts/test_tour_pages_browser.mjs | checkRoutePage、checkMediaPage、checkPresentationShell；桌面与窄屏检查，记录同源结果 |

推荐回归：

```text
python -m unittest discover -s scripts/production -p "test_tour*.py"
node --test scripts/production/test_tour_presentation.mjs scripts/production/test_tour_route_panel.mjs scripts/production/test_tour_playback.mjs
```

每次交付至少生成一次全新目录，再进行真实点击；修订旧页面截图或只数测试数量不算新生成验证。
当前户型、具体房间顺序、75秒等时间、配音音色、音乐、文案和端口留在案例配置中；
临时bug、实现细节、测试输出与未验证猜测不写入Memory。本SOP不自动发布任何内容。
