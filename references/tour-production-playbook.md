# 参观视频制作手册（从户型文件到整片）

给要新做一个户型参观视频的人（或 Agent）：按这一份走完全流程，细节分别指向各专题文档。**所有确认、例外和规则放宽都来自用户的原话，Agent 不代签、不自己编。** 数值只在 1 号户型验证过，耗时是实测参考。

## 流程总览

| 阶段 | 做什么 | 用户要做什么 | 门槛 |
|---|---|---|---|
| ① 路线 | `plan-route` 生成路线页 | 看路线页，说“确认路线” | `homeowner-spatial-approval/1` |
| ② 镜头预演 | `brief-from-route`、`tour-draft`、`plan-tour` | 看预演，说确认；规则放宽逐项同意 | `homeowner-route-approval/1`（镜头预演确认） |
| ③ 视频审阅 | 渲染评审片（H5 或 Blender） | 看视频，说确认 | `homeowner-video-approval/1` |
| ④ 讲解成片 | 合成配音、字幕、音乐 | 提供声音，确认成片 | 视频确认之后 |

阶段之间互相绑定哈希：改了路线、镜头、户型文件，后面的确认全部失效，需要用同一批原话重新记录。

## 0. 开始前

- 户型文件（production bundle）里结构、布局、风格三项必须是“已确认”才能做 Blender 和 H5 正式生产；低分辨率评审路径（`--preview`）不要求。确认来自用户：工作台里点击，或用户在对话里看过平面图后原话确认并明确委托助手写入（来源记 `explicit_user_chat_confirmation`，证据写原话）。写入后户型文件哈希会变，路线和镜头确认要用原话重新记录，镜头本身不变。
- 入户门用 `entranceOpeningId`（形如 `W09:0`）或 `caseFile` 的 `entranceOpenings` 指定，必须是外门。
- 用户的目标是干练、直观、用最短时间讲清房子；时长数字只是估计。

## 1. 路线

`h5.py plan-route --job JOB --out DIR` → 展示 `route.html` → 用户确认后 `h5.py record-route-approval --pending DIR/spatial-review.pending.json --confirmed-by 姓名 --evidence 原话 --out 新文件`。路线好坏由用户判断，不要用数字下结论。

## 2. 镜头预演

1. `h5.py brief-from-route --plan … --out … --maximum-seconds N`，总时长、覆盖、视高原因由案例给出。
2. `h5.py tour-draft` 秒级迭代，`h5.py plan-tour --job … --out …`（约 12 分钟）出正式预演。选项和 1 号经验见 [tour-camera-options-and-lessons.md](tour-camera-options-and-lessons.md)。
3. 读 `camera-diagnostics.json`（回摆、朝墙连续段、时间构成），向用户指出具体几秒。
4. 工程检查没过的项，要么修，要么列成逐项的案例例外，附用户原话；转头速度、加速度、近墙秒数、画面占满秒数都有对应的 `*_limit_override` 例外。预演状态要变成 `pending_user_review` 才能确认。
5. 用户看完整段动态预演后，写连续播放审阅（`route_rehearsal.py bind-quality --manifest … --screen-audit … --visual-review …`，四项：转场自然、无重复介绍、无长时间遮挡、无不适转头，证据用原话）；它会把镜头确认重置为待确认，之后再 `h5.py record-approval --kind camera`。

## 3. 评审片

### 3a. H5 低分辨率评审片（约 7 分钟，无声）
需要“明确授权的评审片”记录：`homeowner-review-capture-release/2`，绑定镜头确认、渲染器、`h5.py audit` 的净空审计和规则指纹；`h5.py capture --preview --full --route-review … --review-release …`；再用 ffmpeg 把 `frames/frame-%06d.png` 编成 mp4。它不是验收，也不能出高清。
- Playwright 参数必须写到 `…/node_modules/playwright/index.js`，写目录会报 `ERR_UNSUPPORTED_DIR_IMPORT`。

### 3b. Blender 整片（默认用于质量；远程 Windows 的 OptiX）
顺序不能跳：
1. `h5.py render-prepare`（需要镜头确认和连续播放审阅都有效）。
2. 灯光配置（[blender-lighting.md](blender-lighting.md)）→ 5 张代表帧静态样板（`run_production.py --engine blender --frame N --render-profile …`，本机每张约 27 秒）→ 用户看样板、原话确认 → 记录静态样板确认。
3. 三段 5 秒动态短样验证：门洞、卫浴、窗景平移（窗口里不要有近表面警告；短样的相机锚点必须是静态场景相机所在的帧；闪烁诊断对取回的 `draft.mp4` 解码后算）。每段需要 `blender_dynamic_draft` 授权，只覆盖那 5 秒。
4. 灯光校准审阅（工程复核，不是用户验收）+ 房间灯光配置 + 整片授权（`blender_review_film`，精确覆盖全部帧，证据是用户要求渲整片的原话）。验证结果文件里去掉指向远程执行记录的引用，避免把 Windows 路径带进整片任务。
5. 远程执行：用户明确选定端点、给出 SSH 别名并授权；`h5.py remote-production --action prepare|start|status|collect|resume`。
6. 质量档：见 [blender-render-speed.md](blender-render-speed.md)，32 采样加显卡降噪 1.65 秒/帧，默认 64 采样 CPU 降噪 4.8 秒/帧；整片中途不换质量档。

### 远程渲染的做法与坑
- 一个远程工作目录只用一次；失败或改了授权就换新目录，并在授权证据里写明原因。
- 状态：`status` 看 `stage` 和 `completedFrames`；阶段是 rendering、verifying_frames、encoding、ready_for_review、failed。
- **暂停**：只结束本任务自己的 `blender.exe`（按命令行里包含任务目录名匹配），不要动同机其他任务；任务会变成 failed 且保留帧；**续渲**用 `--action resume`，已有帧按哈希复用，作业必须与原来完全一致。
- 监视器 30 分钟会过期，长任务每 5 分钟查一次状态，别把一次查询当成实时画面。
- 本机的网页预览服务随会话关闭，视频要长期看就直接用文件。

## 4. 汇报模板

分开写：代码机制测试、真实路线与渲染检查、仍需用户确认的项；只在一个户型验证过的写明；不说“画面更好”除非实际看过；失败的实验如实写，不删。
