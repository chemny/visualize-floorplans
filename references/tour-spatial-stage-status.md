# 路线与镜头拆分：实施状态

详细规则见 `unified-tour-production.md`，整条流程见 `tour-production-playbook.md`，镜头选项和经验见 `tour-camera-options-and-lessons.md`。下列“已接入”指代码路径和回归测试；真实案例（1 号）已走完路线、镜头预演、Blender 评审片、视频确认和讲解成片，四个阶段的确认都来自用户原话；这不代表其他案例通过了确认。

## 已接入

- 路线：`h5.py plan-route`（`tour_spatial_plan.py`）、`record-route-approval`。
- 路线门槛：`plan-tour`、`design-tour`、`route_rehearsal.py` 命令行的路线批准入口检查；Python 与直接浏览器捕获的路线链检查；Blender 与远程经 `require_route` 继承同一检查；镜头候选越出批准范围时退回路线确认。
- 镜头：`brief-from-route`（按已批准路线生成 brief，并在开跑前核对 brief 与路线一致）、`tour-draft`、`optimize-stations`、`camera-diagnostics.json`。
- 确认记录：`record-approval --kind camera|video|narrated`（只接受用户姓名和原话；`narrated` 的 `--pending` 指向 `composition-report.json`，绑定确切成片、字幕和视频确认，`record_approval.require_narrated` 校验）、动态预演的用户确认字段、`h5.py tour-stage-status`。
- 回归：`validate-corpus`（输入缺失或方案哈希不符的案例标为跳过）。

## 已知限制

- 通过 `route_rehearsal.build` 的 Python 接口可生成 `spatialGate: missing` 的诊断预演，这类预演无法进入捕获。
- 站位可视比例是二维墙体代理；门外通行范围是实际入户门处声明的外部区域，不是建模走廊。
- 视频到讲解仍由 `tour_stage_gate.py` 校验确切视频和 tour；上游 bundle 变化由 `tour-stage-status` 报告，`narration-prepare` 本身不重新校验路线。
- 镜头选项和耗时数值只在 1 号户型验证过；2 号、3 号只验证过“能跑、规则不误报”。
- 讲解阶段只校验和合成用户提供的已对齐配音与音乐，Skills 不生成配音。
