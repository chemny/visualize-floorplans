# 全屋参观规则与执行对应表

当前执行版本：`homeowner-tour-rules/2`。规则版本及公共引擎源码指纹同时绑定报告。
历史通过、新数值通过、真实画面通过和用户确认分别记录，互不替代。

## 统一规则

1. **同一相机预设**：所有生成入口读取 `assets/h5/tour/homeowner-profile.json`，默认视高
   1600mm、水平视角76°、零投影偏移、无头部晃动。最终帧须与配置一致。俯仰、房间朝向、
   连接朝向及视高分别修改；不把案例的左偏角或俯视角变成共享默认值。
2. **平顺路径**：直路可以是直线，转弯使用安全圆角。圆角失败时尝试更小安全半径，
   全部失败必须报错/重选路，禁止回退尖角后当作合格。检查最终帧速度向量，包含章节接缝。
   初始审查上限：平面加速度3m/s²；移动速度大于0.05m/s时相邻帧行走方向变化12°。
   这些是保守产品阈值，不是行业标准或舒适度保证。生成器不能擅自改大阈值；用户明确
   批准的案例例外须按下文精确作用域记录，不能替代其它轨迹和安全检查。
3. **观察与行走协同**：稍入房间后展示整体，默认一点、最多两点。相邻区域代看只在
   `observationRegionId`/`coveredRoomIds` 与 `adjacentViewReason` 有真实依据时使用。
   退房面向出口及通路；正常再次入镜允许，主动返扫不因标成 transit 而豁免。
4. **一次完成介绍**：连续访问内单向完成主要构图。进房已经展示主体，随后反向扫回
   同主体也算重复。真实网格屏幕射线同时检查连接和观看，区分顺路入镜与刻意转头。
   邻接同房间的移动观看是连续延伸，不另增家具停点。首次接近下一房间时自然看到其
   物体、沿同一方向连续揭示，不因跨过章节边界就算二次介绍。先前已有可读的正式介绍，
   或已有独立的主动展示后再次扫回，才具备二次介绍依据；首次访问内真实反向仍拦截。
5. **覆盖不能事后补齐**：正式检查按首个连续访问窗口计数，不能靠之后经过补面积。
   Passage-only 空间使用首次实际经过；从相邻房间表达的空间须显式声明。
   无 config 的旧覆盖接口仅作全片诊断，报告注明 `whole_timeline_diagnostic`，不能替代门槛。
   分母保持完整房间；水平代理不等于实际三维可见面积。
6. **完整预算必填**：每个有意观看的房间都须给完整进入/观看/退出预算和案例总上限。
   单点默认最大3秒，位置与朝向同时静止不超过0.5秒。预算不是生成器自行猜测的房间定额。
   缺失预算可输出诊断，不能当作合格。最少观看时间用 `viewingDurationFloors`；要求完全不变
   时另给 `timingLocks:{fps,totalFrames,viewingFrames:{章节名:帧数}}`，可附 `totalSeconds`。
   不把“不得缩短”解释为“精确不变”，也不把“60秒上限”解释为固定60秒。
7. **全片构图检查**：使用实际三角网格屏幕首个不透明命中，覆盖进、看、退及开头结尾。
   初始阈值为15条屏幕射线、4Hz采样；0.9米内表面占比达到60%，或2米内同一表面占比
   达到80%，持续超过0.75秒需修订；空白射线占比90%持续超过0.5秒需修订。
   开场门扇短暂经过允许，结尾离开入户门后仍须有有效收尾构图。
8. **主体可读而非闪现**：除旧主体采样外，至少0.5秒连续构图，主体投影面积占比
   0.5%–80%，至少35%的主体采样点在画幅内。过近、裁切或只露一点需修订；
   这些仍是几何代理，不是截图语义理解。特写只可用针对章节/对象的 `detail_view` 例外。
9. **必填与例外有范围**：正式观看须有真实目标、roomId、viewPurpose、tourRole。
   禁止全局 `subjectRepeatExceptionReason` 或旧 `repeatReason` 放行全片。
   统一使用 `ruleExceptions`：重复/特写记录 `{code,chapter,subjectId,reason}`，必须精确到
   章节和对象；相机、运动、观察点、连接占比、轨迹和视觉阈值放宽须分别说明原因。
   覆盖与单顶点轨迹例外遵守下文严格schema。理由不授予用户确认。
10. **选优检查真实证据**：基线及候选使用相同的检查口径，数值失败不再跳过真实网格/
    全时间线屏幕检查。资源耗尽的候选显式记为未检查，不能靠少报视觉问题取得更好排名。
    资源在初始检查与各修正轮之间保留配额。最终结果继续检查。网格失败的章节及时间段
    反馈至局部候选搜索；真实播放失败的同源镜头不得因一次数值通过被重新标为可交付。
11. **旧证据失效**：源码指纹、路线、配置、几何、场景、渲染器及展示页面必须绑定。
    旧连接端点未变也须复核轨迹；旧报告版本或源码指纹不同需重新审计，不自动迁移验收。
12. **视觉失败优先**：`readyForVisualReview` 仅说明数值/网格检查允许开始视觉审阅。
    实际播放失败时 `reviewable:false`、`productionReady:false`；保持用户批准 pending。
    截图抽样只能记为抽样，不能填 continuous_playback。任何视频捕获还要求同源通过的
    screenAudit 和真实连续播放记录（审阅人、说明及四项检查均明确），Python/JS入口一致拒绝缺失、
    失败、过期记录。用户路线确认不能抹掉已知视觉失败。明确授权的低清评审片按
    `route-rehearsal-gate.md` 的 /2 release 走独立入口；它不改写失败/待审事实，
    不豁免碰撞、数值、覆盖、预算和主体门槛，不含案例固定问题数量或镜头参数。

## 执行与测试映射

| 执行 | 代码 | 回归证据 |
|---|---|---|
| 连续交互播放与局部平顺性提案 | `tour_playback.py`、`rehearsal-player.js`、`tour_motion_comfort.py`、`tour_motion_compare.py` | `test_tour_playback.py/.mjs` 验证分数帧插值、单次交互绘制、捕获接口保留和模块绑定；`test_tour_motion_comfort.py` 验证局部范围、物理边界速度及拒绝不安全提案。样段不替代全片验收 |
| 视线代理与实体碰撞分开 | `Planner.vision_leaves`、`clear_distance` | `test_tour_visibility_geometry.py`：斜门板不填满包围盒、平端墙不缩窄洞口、透明淋浴仍阻挡身体，真实网格审计仍独立执行 |
| 窄通路的前向构图偏好 | `navigation_gaze` 的案例 `preferredHeadingDegrees` | `test_tour_navigation_preference.py`：收紧软偏好可减少斜看，旋转后的路线仍有效，端点构图保留；非法参数拒绝，最终运动/屏幕检查不豁免 |
| 显式面积参考口径 | `tour_coverage.py`、`tour_contract.py` | `test_tour_coverage.py`、`test_tour_contract.py`：保留比例、差额及待审状态；默认硬门槛不变，不豁免倒走或碰撞 |
| 场景核心功能独立核对 | `tour_core_targets.py/.mjs`、`core-functions.json`、`tour_contract.py`、mesh及捕获入口 | `test_tour_core_targets.py` 的遗漏、同框、互补点、首次访问、瞬时/过小与双语言一致性；`test_tour_core_mesh.mjs` 使用实际三角网格测试漏项、背后、遮挡与正例 |
| 抬高设施的真实取景高度 | `tour_camera_evidence.target_anchor/target_samples` | `test_tour_camera_evidence.py` 核对灶台、水槽的 elevation 加本体半高；未抬高家具保持原高度。几何目标高度不代替实际网格可读检查 |
| 正常向前走、退场面向门外 | `tour_forward_motion.py`、`tour_contract.py`、`navigation_gaze`、`JointPlanner.closing_pose` | `test_tour_forward_motion.py`：持续倒走、跨章节、静止/慢速、侧看、角度跨零、正常折返及东西两侧出口；最终帧契约拒绝，JS捕获要求同源检查 |
| Blender与远程捕获不可绕过路线批准 | `blender_draft.py`、`route_rehearsal.py`、`remote_production.py` | `test_blender_route_gate.py`：缺失/待审/变更展示页、几何、场景、路线拒绝；重定位保留叶JSON身份 |
| 参数、必填、范围例外、精确时间锁 | `tour_rules.py`、`tour_contract.py` | `test_tour_rules.py` 的五种漏检、配置一致性、作用范围、时间锁测试 |
| 安全圆角、最终轨迹 | `plan_route.py`、`compact_tour_visits.py`、`tour_rules.trajectory` | 圆角失败不得退回折线；安全圆角正例；最终帧接缝冲击反例 |
| 首次访问覆盖 | `tour_coverage.py`，正式入口显式传 config | 后续途经不能补足第一次漏看的反例；分母、墙遮挡和时间锚定既有测试 |
| 精确案例例外 | `tour_rules.trajectory`、`tour_coverage.py` | 单房间例外不放行另一房间；单顶点例外不掩盖第二处超限；缺理由、未知/重复/越界作用域拒绝 |
| 全片遮挡、重复、构图 | `tour_mesh_preflight.mjs`、`tour_screen_quality.mjs` | `test_tour_screen_quality.mjs`：冰箱/墙占屏、柜面、空白结尾、主体裁切、进房返扫及自然经过正例 |
| 章节末尾的连续首次揭示与正常慢速退出 | `tour_screen_quality.mjs`、mesh逐样本速度 | 连续投影、相机单向和屏幕中心单向才识别为延续；丢失后再出现、屏幕回扫及缺投影证据仍按重复检查。慢速退出须真实移动且向通行方向收敛，静止、离开路径朝向和持续背行不获豁免；最终倒走契约仍独立拦截 |
| 冻结外部帧的局部角度修订 | `tour_gaze_repair.py` | `test_tour_gaze_repair.py`：授权轴与窗口之外逐值不变，保留帧数/位置/时间；不收敛和不可连接边界拒绝 |
| 原生门洞构图与有限修正 | `tour_doorway.py`、`tour_pipeline.py` | `test_tour_doorway.py`：真实孔径、旋转/改名、误拍墙修正、冻结外部；`test_tour_pipeline.py`：软缺口触发修正、软分不能抵消硬失败 |
| 标准修订范围与阶段收口 | `tour_pipeline.py`、`tour_revision_review.py` | 越界一帧拒绝、searchOnly无HTML、工程结果独立；`scripts/test_tour_revision_review.py`：过期证据/未绑定人工记录/外景失败不得冒充通过 |
| 新规划与修订的时间边界 | `tour_pipeline.JointPlanner.observation_frames`、job `planningMode` | `test_tour_pipeline.py`：新初稿不继承膨胀时长，移动观看按实际转向分配，显式锁不足拒绝，默认修订及显式下限/时间锁保留 |
| 显式分阶段功能介绍 | `tour_core_targets.py/.mjs`、`tour_coverage.py`、`tour_room_budgets.py`、`tour_camera_evidence.py` | 核心设施首次明确介绍绑定、缺理由不启用、后续经过不补漏、分段预算与覆盖、单次过程内部反扫仍拒绝 |
| 新规划的安全运动与曲线保留 | `tour_pipeline.py`、`tour_speed_profile.py` | `test_tour_pipeline.py`：真实障碍物弧线不拉直、固定观察点不漂移、加减速/转向计时、精确锁不足拒绝；默认修订及冻结范围回归 |
| brief 意图完整传递 | `design_homeowner_tour.py` | `test_tour_design.py`：无序目标不被顺序列表覆盖，显式面积参考策略保留，外置干区跨物理区域连接不伪装为房内移动观看 |
| 候选选优与反馈 | `tour_pipeline.py` | 候选真实网格调用与排序、已知播放失败、旧连接轨迹重检测试 |
| 源码失效、视觉失败门槛 | `route_rehearsal.py`、`preview_gate.mjs` | 两种入口均拒绝缺失屏幕审计、旧引擎指纹、抽样冒充完整播放、失败播放记录 |

单元测试使用明确标识的合成证据测试门槛，不能当作真实房屋视觉验收。
真实案例复核使用 `audit_tour_rules.py` 与离线 mesh preflight；仅写新报告，不改源案例。
没有真实播放时必须保留 pending，不因某个检查数量通过而宣称画面合格。

## 审核呈现能力

渲染执行、降噪/局部稳定性、可选放大及最终交付采用
[制作执行与交付契约](production-execution-and-delivery.md) 的原生入口及回归映射。
执行契约为 `homeowner-production-sop/1`；它不改变原路线契约、不授予用户批准。

呈现规则的唯一规范与逐项实现/验收表在 [四阶段审核呈现 SOP](tour-presentation-pages.md#6-规则实现验收清单)。
规划、摄像机数值/网格验收与页面功能检查分开。标准生成入口与捕获后的页面入口均使用同一共享呈现器。
不得以对照工具、嵌套旧页或病例专用外壳替代四阶段页面。此处不复制版式细则，避免多份规则冲突。

## 精确案例例外

仅在用户明确批准后写入该案例配置的 `ruleExceptions`，不改共享默认值：

- 覆盖：`code: room_coverage_minimum_override`，必填 `roomId`、`minimumPercent`、
  `reason`。`roomId` 必须属于当前模型，最低值为有效百分比且低于案例默认最低值；
  同房间不得重复声明。完整多边形、采样和首次访问窗口保持原口径，其它房间继续用默认值。
- 单顶点行走方向：`code: path_tangent_step_override`，必填 `chapter`、`offsetFrame`、
  `maximumDegrees`、`reason`。章节名须唯一，偏移是从该章 `from` 标记起算的非负整数帧，
  落在该章左闭右开范围内且为全片内部顶点；上限须有效且高于默认值。只放行这一顶点，
  其它顶点逐一检查，不能用最高峰已获例外掩盖第二处超限。碰撞、步速与加速度不放宽。

未知、缺理由、重复或越界作用域拒绝执行。报告保留默认门槛、例外理由、实际测量与
是否用到例外；覆盖比较使用未取整采样比例，不能以显示四舍五入代替真实门槛。

## 自动修正必须具有的实际动作

- `tour_candidate_quality.py` 统一附加屏幕检查与历史失败状态。微小角度变化、位置变化
  或数值通过不清除失败；需要新的适用几何检查。几何通过仍不代替实际动态播放。
- 真实观看和 `movingView` 都进入候选搜索。连续观看段共享边界机位与朝向，没有额外
  的隐形连接或新增停点；固定观看帧数从窗口构建开始执行。某个候选连线失败只排除
  该候选；联合搜索在早期房间失败，后面房间仍可获得局部候选。至少两个beam分支时
  保留一个兼容的基线链，避免前段局部低分占满分支、后段却全部接不上。保留基线不代表
  基线合格，仍须检查路径、画面和全部预算。
- 连接预算在组合候选时提前筛查。精确总时长分配使用实际行走、偏航、俯仰工作量，
  允许回收旧连接中的低效时间；不能把旧连接帧数误当无法再短的理论下限。该筛查是
  可行性下界，最终运动、碰撞与覆盖检查仍不可省略。
- 章节接缝同时修正位置与速度：安全空间内尝试相切曲线；窄门可沿既有安全路径
  减速后转向。边界位置与帧数保持；真实折返不能用平滑朝向掩盖瞬时反向。候选不安全
  或未改善时保留失败，并重选观察位置；不以放宽加速度、穿墙或加时强行通过。
- 纯俯仰/朝向修改可复用经过轨迹与碰撞复核的原空间连线，独立重算视线及计时；
  不能因镜头变了就丢掉安全空间路径，也不能因空间端点相同就跳过接缝与镜头检查。
- 内部局部角度修订可调用 `tour_gaze_repair.revise`：显式给连续章节窗口、授权轴及
  帧偏移角度键；其它帧和未授权轴逐值冻结，位置、帧数、访问标记和时长保持不变。
  投影同时约束窗口接缝与观察单向性，未收敛即拒绝；完成后仍须完整复核覆盖、运动、
  遮挡、主体与重复。该helper可供编排器调用，不表示所有 `plan-tour` 候选已自动接入。
- 与冻结基线比较，候选不能新增原本已满足的房间覆盖、完整进出预算、运动或精确时间
  失败。按房间/章节/轴区分，厨房原有失败不授权把餐厅弄坏。修复反例和候选失败都保留
  诊断，不以减少视觉提示数为由破坏其它已确认约束。
- 完整看房的末端保持已确认入口和位置，沿门洞指向门外终点的方向退场，禁止倒着走出门；重新计算
  转头工作量并检查真实网格。旧末帧仅作为显式失败基线与分步修正的诊断候选，不能默认为
  合格；门口构图不强塞进每个房间的修正预算。暂缓收尾修正时保留空白结尾失败，不能
  据此批准捕获；不凭空补造室外走廊。
- 局部备选数量按成功构建并进入完整评估的候选计数。先遇到不可连接、超预算候选时，
  在总时间与候选上限内继续下一个备选，不能让第一个无效方案耗尽该房间的唯一机会。
  错误报告须记录章节、退场模式及实际/可用帧数。
- 垂直构图以物体旋转后的上、下边界投影评分，俯仰候选可以向上、向下调整。
  8°/10°俯视仅为候选起点，不是新的全屋统一角度；先换合适站位，再比较实际网格遮挡。
  视高仍默认1600mm，水平视角仍默认76°，不自动降低视高或增加全程俯视。

上述行为的反例在 `test_tour_candidate_quality.py`；`test_tour_pipeline.py` 另验证数值失败
仍调用真实网格检查接口。`searchOnly:true` 执行内部候选与最终检查，仅输出数据和报告，
不生成HTML预演、不复制页面runtime、不生成视频。规则修改应先使用此模式核实，不反复
向用户展示尚未达到门槛的预演。

## 审阅记录绑定

统一规划输出 `visual-review.pending.json`，始终留空审阅人并标 pending。
真实审阅后另存记录，不覆盖原记录。用以下命令绑定同源证据并让旧批准失效：

```text
python scripts/production/route_rehearsal.py bind-quality --manifest REHEARSAL_MANIFEST --screen-audit CURRENT_MESH_AUDIT --visual-review ACTUAL_PLAYBACK_REVIEW
```

该操作不签署用户确认。画面、预算或引擎变化后重新展示并确认。规则配置修改和当前案例
预演更新是两个独立任务；只授权修改规则时，不自动重建、迁移或覆盖预演。

- 互补观察窗各验声明构图，核心设施在首次完整区间独立核对：`tour_mesh_preflight.mjs`，实际三角网格双窗反例见 `test_tour_core_mesh.mjs`。
- 局部运镜修订保留原运动上限，固定区间不受额外收紧；精度只可收紧，默认资源预算不变：`tour_gaze_repair.py`、`tour_connection_motion.py`，反例见 `test_tour_gaze_repair.py`。
- 连接预留时间与实际运动限制分离，案例可显式选用较小规划预留；最终检查不豁免：`tour_speed_profile.py`，校验见 `test_tour_speed_profile.py`。

视频审阅与讲解制作之间的执行关卡：`tour_stage_gate.py`，共享 `h5.py narration-prepare/compose` 与生产页面包装均调用；见呈现 SOP“制作顺序与执行关卡”。反例及实际短媒体回归为 `test_tour_stage_gate.py`。

## 四阶段拆分

| 规则 | 实现 | 回归 |
|---|---|---|
| 路线不依赖镜头、帧 | `tour_spatial_plan.validate_job`、`build` | `test_tour_spatial_plan.RoutePlanning` |
| 外部范围未声明与真实碰撞分开 | `tour_spatial_plan.explain_point`、`opening_passability` | 同上 |
| 路线确认绑定计划、页面、bundle，代理和夹具不能签名 | `tour_spatial_plan.require_approval` | `ApprovalGate` |
| 镜头入口消费路线确认 | `tour_stage_chain.require_camera_entry`（`tour_pipeline.run`、`h5.py design-tour`、`route_rehearsal.main`） | `EntryGates` |
| 镜头不越出批准范围 | `tour_spatial_plan.conformance`、`tour_pipeline.attach_spatial_evidence` | `Conformance` |
| 捕获重验路线链 | `tour_stage_chain.require_rehearsal_chain`（`require_route`）、`preview_gate.mjs requireSpatialChain` | `EntryGates`、`test_review_capture_release.mjs` |
| 动态预览需用户确认 | `tour_workflow.require_preview`、`preview_gate.mjs requirePreview` | `test_tour_workflow.py`、`test_preview_gate.mjs` |
| 上游变化阻断下游状态 | `tour_stage_chain.evaluate` | `StageState` |

合成批准使用 `approvalSource: synthetic_test_fixture`，仅在测试显式打开模块开关时通过；命令行、任务文件和环境变量都无法打开。
| 连接转头最少、不转圈 | `design_homeowner_tour.forward_plan`（连续展开 yaw） | `test_tour_flow_camera.MinimalTurning` |
| 扫视联合选择 | `flow_candidates`、`forward_plan(coarse=True)` | `test_tour_flow_camera` |
| 小房间回退及限额 | `tour_forward_motion`（`SMALL_ROOM_AREA_M2`、`BACK_OUT_*`、`verify_policy`）、`back_out_hold`、`tour_contract` | `test_tour_back_out.py` |
| 重排连接不得引入转头过多或倒走 | `tour_candidate_quality.protect_satisfied_constraints` | `test_tour_candidate_quality.ProtectedConstraints` |
| 对照版带画面检查、检查预算与预留 | `tour_pipeline.run`（`baseline_contract`、`phase_mesh_limit`、`_finalDeadline`） | 无专门单测；由完整规划运行核对 |
| 走路俯仰与视高 | `design_homeowner_tour.design`（`pitchPolicy`）、`tour_rules.py`（`camera_profile_override`） | 无单测；只在预演里目视核对 |

镜头选项的键、默认值、验证范围见 `tour-camera-options-and-lessons.md`。
| 停顿缓停缓起、巡航分档 | `tour_workflow.shaped_distance_times`、`design_homeowner_tour.mark_speed_limits`、`tour_stop_smoothness.inspect`（`abrupt_stop`） | `test_tour_smooth_motion.py` |
| 小空间只在门口、终段加速度限制 | `tour_small_room_depth.inspect`（`small_room_too_deep`）、`tour_workflow.limit_acceleration` | `test_tour_smooth_motion.py` |
| 房间内回摆、近墙连续段、时间构成诊断 | `tour_camera_diagnostics.room_wobble`、`wall_facing_runs`、`time_breakdown`（只诊断，不判定通过） | `test_tour_spatial_plan.py` Diagnostics |
| Blender 灯光配置键与单灯功率 | `blender_lighting_profile.validate`、`fixture_power`、`brightness_report`；`import_blender.configure_lighting` 调用 | `test_blender_lighting.py` |
| Blender 提速对比（相似度、峰值信噪比、放大对比图）与快速质量档模板 | `compare_render_quality.py`、`blender-quality-fast-template.json`、`blender_render_quality.validate` | `test_compare_render_quality.py`、`test_blender_render_quality.py` |
| 本案转头速度上限覆盖 | brief `motionReviewLimits` + `motion_limit_override` 例外；`design_homeowner_tour` 读取 | `test_tour_rules.py` |
| 路径舒适净空（离墙偏好，不绕路） | `plan_route.Planner.cell_gap`、`design()` 的 `route()` 回退规则 | `test_tour_smooth_motion.ComfortClearance` |
| 连接段转头：绝对 ≤180° 且比路线自身转弯多出 ≤90° | `tour_choreography.inspect`（`path_turning`、`transit_turn_beyond_path`），受 `protect_satisfied_constraints` 保护 | `test_tour_turn_limits.py` |
| 路线确认记录只来自用户原话 | `record_approval.record_route`（`h5.py record-route-approval`） | `test_tour_spatial_plan.RecordApproval` |
| brief 与已批准路线一致、经过不看的站位要列出 | `tour_stage_chain.check_brief_alignment`、`pass_through_stations`（`tour_pipeline.run` 开跑前调用） | `test_tour_spatial_plan.BriefAlignment` |
| 从已批准路线生成镜头 brief 与假设清单 | `brief_from_route.build`（`h5.py brief-from-route`） | `test_tour_spatial_plan.BriefFromRoute`；三个真实户型的 `design()` 运行 |
| 按章节的镜头诊断 | `tour_camera_diagnostics.build`（输出 `camera-diagnostics.json`） | `test_tour_spatial_plan.Diagnostics` |
| 秒级镜头草稿 | `tour_draft.draft`（`h5.py tour-draft`） | `test_tour_spatial_plan.CorpusRegression`（合成案例走完整前半链） |
| 站位按网格画面联合选择并复核撤销 | `optimize_stations`（`h5.py optimize-stations`） | `test_optimize_stations.py` |
| 案例成绩表与基线比较 | `validate_case`（`h5.py validate-corpus`）、`assets/regression/tour-corpus-manifest.json` | `test_tour_spatial_plan.CorpusRegression` |
| 镜头预演、整片视频确认记录 | `record_approval.record_camera`、`record_video`（`h5.py record-approval`） | `test_tour_spatial_plan.StageApprovals` |

