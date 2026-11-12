# 镜头预演（第②阶段）：选项、默认值与经验

本文是第②阶段（镜头预演）的使用说明和经验汇总。**所有镜头选项默认关闭，数值只在“当前家装助手三室两厅两卫”（1 号）一个户型上调试过**；路线阶段另在 2 号、3 号上跑过。没有在陌生户型上独立验证，不能当作通用有效的证据。灯光与渲染见 [blender-lighting.md](blender-lighting.md) 和 [blender-render-speed.md](blender-render-speed.md)；整条制作流程见 [tour-production-playbook.md](tour-production-playbook.md)。

## 0. 新案例清单（按顺序走，能少绕路）

1. **路线**：`h5.py plan-route --job`（模板 `spatial-job-template.json`，最少只填 bundle 和入户门；入户门用 `entranceOpeningId`，如 `W09:0`，或 `caseFile` 里的 `entranceOpenings`）。展示 `route.html`，不要自己判断路线好坏。
2. **记录确认**：用户明确接受后，`h5.py record-route-approval --pending … --confirmed-by 用户姓名 --evidence 用户原话 --out …`。工具拒绝代理名称和空原话；不要为了往下走自己编。
3. **镜头 brief**：`h5.py brief-from-route --plan 已批准路线的 spatial-plan.json --out 新目录 --maximum-seconds N --coverage-minimum-percent P`（诊断用可改 `--coverage-off`）。它按路线顺序和站位生成 `brief.json`，并写 `brief-assumptions.json`：每站的主体与来源、停留秒数、房间预算、归属调整、经过不看的站位、需要人核对的项；小空间（单门、6 平方米以内、非入户首个房间）的站位会移到门内 400 毫米。总时长、覆盖百分比、视高原因必须由案例给出，不会替你填。手写时从 `camera-brief-template.json` 起步；两种方式 `plan-tour` 开跑前都会核对 brief 与路线一致。
4. **镜头 job**：`production-job-template.json`，带 `spatialPlan`、`spatialReview`；`plan-tour` 开跑前先核对，不一致立即报错，不会白跑 10 分钟。
   - **快速草稿（秒级）**：`h5.py tour-draft --bundle --brief --out [--runtime]`，只做镜头设计、平滑、数值检查和诊断，不跑候选搜索；带 `--runtime` 时加一次真实网格画面检查。调 brief 时来回迭代，定下来再跑 `plan-tour`。草稿永远不用于确认。
   - **站位按画面选**：`h5.py optimize-stations --brief --plan --runtime --out`，每个站位在路线容差内试多个位置，按主体读得清、不贴墙、与路线站位的距离联合选；凡引入转头过多或持续倒走的移动会被撤销。在 1 号上读不清的主体 12→10，是小幅改进；一次还曾把站位移到画面评分更差的位置，用前要看它的报告。
5. **读诊断**：`plan-tour` 输出 `camera-diagnostics.json`：按章节的转头、俯仰、对墙秒数、倒走、画面检查问题的时间；另有 `roomWobble`（每个房间到达前 2 秒到看完后 2 秒的左右回摆）、`wallFacingRuns`（正前方不到 60 厘米的连续段及所在章节）、`timeBreakdown`（原地秒数与行走米数）。用户说“来回晃”指房间内的回摆，不是连接段。向用户汇报时用它指出具体哪几秒，不要只报问题个数。
6. **预演**：用内置浏览器打开 `preview.html`，拖 `#seek` 看画面；无头浏览器可能渲染不了三维。
7. **回归**：`h5.py validate-corpus --manifest assets/regression/tour-corpus-manifest.json --out 新目录`，对清单里每个案例一键跑路线、brief、镜头草稿并与基线比较；阶段失败、新出现的转头过多或持续倒走、最大转头增加超过 15°、路线站位变化、路线变长 10% 以上都会被点名。基线记录的是数字，不是质量。清单里的路径指向作者机器上的案例文件，找不到输入的案例会标为“输入缺失，已跳过”，不算失败。
8. **确认记录**：路线 `record-route-approval`；镜头预演和整片视频 `h5.py record-approval --kind camera|video`。都只接受用户姓名和原话，拒绝代理名称、空原话、示例视频和还需修改的预演（镜头预演要等它自己的检查过了才能确认）。
9. **目标与时长**：用户的目标是干练、直观、用最短时间讲清房子，时长数字只是估计。先用 `timeBreakdown` 报停留、原地转向、行走各占多少，说明压时长的代价，不要为凑数字牺牲画面；规则无法通过时，把需要写的案例例外逐项列出，由用户决定，不替用户写。
10. **汇报**：分开写代码机制测试、真实路线检查、仍需用户目视确认；只在一个户型验证过的规则要写明。

## 1. 选项（写在 brief 里，随 `plan-tour` 或 `design-tour` 使用）

“状态”：**用**＝1 号上验证有效；**可选**＝有效但有代价；**未采用**＝试过没有净收益，保留以便复现。

| 键 | 作用 | 默认 | 状态 / 1 号定稿值 |
|---|---|---|---|
| `navigationPolicy.mode: forward` | 连接段用最少转头规划：朝向保持在行走方向 `forwardBandDegrees` 以内，必要时原地转身，进出两次转身的度数都计入 | 关 | 用 |
| `navigationPolicy.forwardBandDegrees` | 走路时镜头与行走方向的最大夹角 | 60 | 用；定稿 85。78° 起出现持续倒走，放宽到 85 省转身时间 |
| `navigationPolicy.lookAheadMm` | 朝前看的预瞄距离 | 900 | 500 到 700 可消去倒走，但总长加 1 到 2.5 秒并带来转头超限 |
| `navigationPolicy.avoidWallFacing` / `wallFacingWeight` | 走路时按正前方离墙距离加成本 | 开 / 2.5 | 用；加大到 10、30 无收益 |
| `navigationPolicy.smallRoomBackOut` | 12 平方米以内、单出口的房间：拍完朝向房间向后退出，最多 1.2 米、2.5 秒 | 关 | 用 |
| `navigationPolicy.smallRoomBackOutMm` / `afterStopBandDegrees` | 小房间回退距离；停顿转身后头一段路更贴近行走方向 | 1200 / 关 | 定稿 800 / 关 |
| `navigationPolicy.smallRoomShallowMm` / `smallRoomShallowAreaM2` | 面积以内、单门的小空间只进门这个深度；入户首个房间除外；违反记 `small_room_too_deep` | 关 / 6 | 用（生成器默认 500） |
| `navigationPolicy.sweepConsistencyWeight` | 联合选择扫视时，把接近转向与扫视反向、上一扫视与离开转向反向按度数计价，减少房间内回摆 | 0 | 可选；权重 3 回摆 10→8，次卧厨房没改善 |
| `navigationPolicy.turnInsideSmallRoom` / `hardWallGapMm` / `hardWallCost` | 小房间退出时允许室内转向，并对近墙前原地转向按步计价 | 关 | 未采用：朝墙 4.1→3.4 秒但总长 +3 秒 |
| `navigationPolicy.comfortClearanceMm` / `comfortWeight` | 路径按“身体边缘离墙”加成本，偏向走廊和房间中间；路径比无偏好的长超过 12% 或多转超过 45° 就退回 | 0（关）/ 2.5 | 用；定稿 450 |
| `panPolicy: flow`、`flowMinSweepDegrees`（24） | 所有房间的扫视联合选：按前后连接要多转多少度打分，主体须停留在画面内，同一房间段保持一个方向 | 关 | 用 |
| `flowSubjects`、`maxSweepDegrees`（房间内） | 只让这些主体决定扫视；该房间扫视上限 | 全部 / 无 | 用；不改变核心设施检查，不能当绕过手段 |
| `pitchPolicy: subject`、`walkingPitchDegrees`、`observationPitchMinDegrees`/`MaxDegrees` | 走路接近平视，观看时按主体高度小幅下倾 | 关；-3 / -16 / -2 | 用；定稿 -3 / -8 / -2 |
| `eyeMm` + `cameraProfile.eyeMm` | 视高；低于 1600 须在 `ruleExceptions` 写 `camera_profile_override` 和原因 | 1600 | 定稿 1300（用户偏好） |
| `speedPolicy` | `cruiseMps` 开阔巡航、`narrowCruiseMps` 近墙或转弯、`rampSeconds` 进入停顿的缓停、`startRampSeconds` 离开停顿的起步（不低于巡航/2，否则被判急起）；只会拉长时间，不会突破运动上限 | 关 | 用；生成器 1.1 / 0.95 / 0.85 / 0.65，定稿 1.2 / 1.05 / 0.75 / 0.7 |
| `motionReviewLimits`（brief 顶层） | 本案转头速度上限；高于 `homeowner-profile.json` 的 32°/s 必须在 `ruleExceptions` 写 `motion_limit_override` 并附用户原话 | 无 | 定稿 `maxYawDegreesPerSecond: 45` |
| `trajectoryPolicy`、`cameraEvidencePolicy`、`visualQualityPolicy` | 加速度、近墙秒数、画面占满秒数等阈值；放宽须写对应的 `*_limit_override` 例外并附用户原话 | 默认 | 定稿见第 4 节 |
| `viewSeconds`（房间内） | 观察点停留；单点上限 3 秒 | 逐房间填写 | 定稿 1.5 到 2.1 秒 |

注意：房间带 `approachViewTargetMm` 时，该房间的连接段绕过最少转头规划，测过会出现 200° 以上来回转。需要“进门时先看到某物”时，先在预演里确认非用不可。

## 2. 引擎层面的通用修正

- **不转圈**：旧的朝前看用折算到 ±180° 的差值，路线方向穿过 180° 时镜头多转一整圈。现在 yaw 是一条连续展开的曲线。
- **转身计入、选最少**：进出各一次原地转身，度数计入总转头；在 `pivot + 行走 + pivot` 里取总转头最少。
- **扫视一起选**：逐房间单独选扫视会让相邻连接多转一圈；现在按整条路线联合选。
- **死胡同房间**：出口方向与观看方向相反，转身无法消除，回退只是把转身挪到门外，总度数仍计入 `excessive_transit_turn`。
- **候选保护**：`excessive_transit_turn`、`transit_turn_beyond_path`、`sustained_backward_walking`、`abrupt_stop`、`small_room_too_deep` 进入 `protect_satisfied_constraints`，重排连接不得引入原本没有的这些问题。
- **对照版要对等**：`baseline_contract` 取已附上画面检查的种子，否则会把做过检查的候选误判为变差。
- **画面检查预算**：第一阶段 3 次（种子 + 两个平滑候选）；`_finalDeadline` 为最终网格检查预留时间，搜索循环用 `_planningDeadline`。
- **终段加速度限制**：`tour_workflow.limit_acceleration` 对相邻走路区间做前后两遍限幅，只拉长不缩短；转头限速、窄处限速叠加造成的速度台阶（如 0.95→0.5 米/秒一帧）被抹平，路径切线突变清零。
- **半帧取整**：停留时间按整帧取整，差半帧以内不再报 `viewing_time_compressed`。
- **全程回到起点**：`full_tour_does_not_return_to_entrance` 要求首末帧同点，所以不能单独截掉结尾几秒。

## 3. 经验与教训

### 路线与确认
- **路线好坏由用户判断，数字不算**。重复路程、自交、总长都变好的排序规则，用户判断为错，已撤回。改排序规则前先问“哪里不对”。
- **“自动”有边界**：入口必须恰好一条且是外门；开放空间按家具分区；自动排序最多 12 站。
- **核心设施与用户要求冲突时**：用户不想单独扫向衣柜，办法是让衣柜随画面带过，不是开例外；目前没有核心设施例外机制，只有每个主体的 `detail_view` 例外（需章节、主体编号和用户原话）。

### 转头与回摆
- **转头上限（用户 2026-11-02 确认）**：连接段镜头转头绝对不超过 180°，同时不得比路线自身的转弯多出 90° 以上（`transit_turn_beyond_path`，`choreographyPolicy.maximumTransitExcessDegrees`）。依据：42 段连接里多出部分中位数 4°、90% 分位 78°；绝对角度会误伤路线本来就拐很多弯的连接。90° 是按数据定的产品门槛，不是标准。
- **房间内回摆**：形态是“接近时朝一侧、观察扫视朝另一侧”。1 号共 10 处，权重 3 的 `sweepConsistencyWeight` 降到 8（定稿版 6）；次卧、厨房没有改善。连接段回摆（门口原地转向后又转回、路径 S 形拐弯）由端点决定，把回摆度数计入扫视选择无效。

### 速度与停顿
- 原数据：走路段全程 1.2 米/秒，约 15 次在 0.3 秒内刹停；路径身体边缘离墙只有安全线。路径舒适净空后最小净空约 50 毫米以上；门洞和窄走廊里几乎没有改善。
- **急停检查**：`abrupt_stop`：静止前 0.4 秒内从 0.8 米/秒以上骤降，或起步 0.4 秒内猛升到 0.8 以上。
- **持续倒走**：背朝行进方向大于 90°、速度大于 0.2 米/秒、连续超过 1.0 秒才判不合格（2026-11-02 起，原 0.5 秒，依据只有 1 号实测 0.58、0.83 秒）；半步回退通过。
- **连接占比**：`transit_dominates` 上限 80%（2026-11-02 起，原 55%；三个户型整屋参观实测 74% 到 76%，原值不可达）。缩短停留反而加重占比。

### 贴墙与朝墙
- 近墙画面出现在门口转身和贴墙行走处。加大避墙权重、走路带内朝墙硬惩罚、改变停下后的朝向范围都没有减少，反而加长时间。原因是走廊宽度：书房门外走廊约 1 米宽，原地转 180° 必然扫过两侧 30 到 60 厘米的墙。转头速度上限从 32 提到 45°/s 是唯一有效的杠杆，也只缩短一点。
- 视角俯视的原因是恒定下倾加高视点；视高降到 1.3 米后低矮家具入画。这个偏好是用户的，不是通用标准。

### 时长
- 1 号 89 秒的构成：停留约 25.5 秒、原地转向约 17 秒、其余为行走与缓停缓起；巡航受 1.2 米/秒上限，提到上限只省约 4 秒。停留缩 25% 总长 80.5 秒但引入转头超限；转头速度上限提到 45°/s 加缩短停留、放宽走路朝向，才到 69.9 秒。
- 回头看，没有一种参数组合同时满足全部检查；通过靠案例例外，每条须有用户理由。

### 验证与汇报
- 只在一个户型上调出的规则，写明“只在该户型验证”。
- 汇报分开写：代码机制测试、真实路线检查、仍需用户视觉确认。
- 不要说“画面更好”除非实际看过；无头浏览器不一定能渲染 WebGL，预演页用内置浏览器。
- 每次引擎改动后重跑全量回归，已知历史错误单独标注。

## 4. 1 号定稿所用设置（参考，不是通用值）

69.875 秒（1677 帧），用户确认镜头预演后渲成 Blender 整片：

- 走路：巡航 1.2、窄处 1.05、缓停 0.75 秒、起步 0.7 秒；`forwardBandDegrees` 85、`lookAheadMm` 900；停留 1.5 到 2.1 秒；小房间回退 800 毫米、门内深度 500 毫米；回摆权重 3。
- 例外（均附用户原话）：视高 1300（`camera_profile_override`）；转头速度 45°/s（`motion_limit_override`）；加速度 7（`trajectory_limit_override`，到站最后一帧实测 6.6）；近墙 1.5 秒（`camera_evidence_limit_override`）；画面占满 1.8 秒（`visual_limit_override`）；书房衣柜 F29、厨房冰箱 F33 读不清（`detail_view`）。
- 全局规则调整：连接占比 55%→80%、持续倒走 0.5→1.0 秒。

## 5. 当前状态与遗留

- **已解决**：不转圈、小房间回退与只在门口、速度台阶、半帧取整、连接占比规则。
- **只能靠案例例外通过**：转头速度、到站加速度、近墙与画面占满时间、两个读不清的主体。
- **没有解决**：书房门外走廊的朝墙和近墙画面（由走廊宽度决定）；次卧和厨房的房间内回摆。
- **只靠人工**：路线对不对、镜头舒不舒服、预演和视频是否接受，没有办法也不应该自动化；工具只负责记录和绑定。
- **验证范围**：数值只在 1 号上调试；2 号、3 号只验证过“能跑、规则不误报”，其生产户型文件现已不在原路径，需要重新导出后才能再验证；站位优化只是小幅改进。
