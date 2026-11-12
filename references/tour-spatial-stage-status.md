# 路线与镜头拆分：实施状态

2026-11-01 已接入，详细规则见 `unified-tour-production.md`。下列“已接入”指代码路径和回归测试，不代表任何真实案例已通过用户确认。

已接入：`h5.py plan-route`（`tour_spatial_plan.py`）；`plan-tour`、`design-tour`、`route_rehearsal.py` 命令行的路线批准入口检查；Python 与直接浏览器捕获的路线链检查；Blender/远程经 `require_route` 继承同一检查；镜头候选越出批准范围时退回路线确认；动态预览的用户确认字段；`h5.py tour-stage-status`。

已知限制：

- `plan-tour` 的 brief/seed 不会读取已批准路线来生成站位，只在候选和最终结果上检查是否符合。brief 顺序与路线不一致时结果是退回路线确认，而不是自动改写 brief。尚无真实案例走完此段。
- 通过 `route_rehearsal.build` 的 Python 接口可生成 `spatialGate: missing` 的诊断预演，这类预演无法进入捕获。
- 站位可视比例是二维墙体代理；门外通行范围是实际入户门处声明的外部区域，不是建模走廊。
- 视频到讲解仍由 `tour_stage_gate.py` 校验确切视频和 tour；上游 bundle 变化由 `tour-stage-status` 报告，`narration-prepare` 本身不重新校验路线。

镜头选项的完整说明已移到 `tour-camera-options-and-lessons.md`，以下为早期摘要：

镜头选项（brief，默认关闭）：`panPolicy: flow` 按整条路线联合选各房间的扫视（逐段估算真实转头量），主体须停留在画面内，同一房间段保持同一方向，扫视不小于 `flowMinSweepDegrees`（默认24°）；`navigationPolicy.mode: forward` 用最少转头的连接规划：朝向保持在行走方向 `forwardBandDegrees`（默认60°，本案72°）以内，必要时在原地转身，进出的转身都计入转头量，不走“长路绕一圈”。`plan-tour` 为最终网格检查预留时间，并禁止重排连接时引入原本没有的转头过多或持续倒走。这些选项不放宽任何检查门槛；带 `approachViewTargetMm` 的房间会绕过最少转头规划，本案已去掉。

小房间回退（`navigationPolicy.smallRoomBackOut: true`，按案例开启，默认关闭）：面积不超过12平米、只有一个出入口的房间，拍完后允许保持朝向房间向后退出，最多1.2米、2.5秒，退出后在门外再转向，避免在小房间里原地转身。限额写在 `tour_forward_motion.py`，案例配置只能收紧、不能放宽；`tour_contract` 用已确认方案核对声明的房间面积。退出以外的位置，持续倒走仍判不合格。回退只改变转身发生的位置，转头总度数仍照常计入。这是产品门槛，不是行业标准。

俯仰与视高（brief，默认关闭）：`pitchPolicy: subject` 让走路接近平视（`walkingPitchDegrees`，默认-3°），观看窗口只按主体高度小幅下倾（`observationPitchMinDegrees`/`MaxDegrees`，本案-8°到-2°），避免全程俯视。视高 `eyeMm` 低于 Skills 默认 1600mm 时，须在 `ruleExceptions` 的 `camera_profile_override` 写明原因；本案按用户反馈降到 1300mm，眼前低矮家具更容易入画。`flowSubjects` 只让指定主体参与扫视选择，其余主体随画面带过，但核心设施（如卧室衣柜）仍须被实际网格检查看到，没有例外机制时不能靠它绕过。
