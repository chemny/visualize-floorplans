# 六维度候选比较：复用布局验收入口

六个维度的定义与已有检查分工统一放在 `furniture-placement-principles.md`，不另设一套家具摆放规则或住宅通用尺寸。本记录由既有 `layout_review.py` 调用 `layout_candidate_review.py` 验证；不会自动优化布局或识别审美。

## 先检查底线，再比较取舍

功能满足、安全操作、必要通行是明确要求的底线；不能靠更大的柜子、更好的外观或加权总分抵消。通过底线后，逐项比较功能适配、空间利用率、便利性、安全与舒适、维护与耐用、视觉协调。没有改变的维度如实写“未改变及其原因”，不能为了显得全面编造优势。产品和现场未知项保留unverified；不能将未知的硬性要求改写成pass。

设计前比较用 `mode: design_comparison`，至少两份不同、实际有方案数据且满足本次硬性要求的候选；不能复制同一布局换名称，也不能只用一个明显不满足需求的方案陪衬。候选不必都做成效果图，先用可编辑几何、功能及操作证据比较；必要的视觉判断另看真实图。若目前找不到两个可行方案，继续比较调整，或明确报告候选不足，不宣称比较完成。

对既有案例补验用 `mode: retrospective_validation`，允许把历史基线作为对照并标明不满足新需求的项；输出可行候选数量，不能倒推“当时已先比较后选定”，也不证明完成了新方案搜索。没有改善依据时保留现状，不为了凑候选改变交付布局。

## case-local record

在现有layout-review/1添加candidateComparison，并按任务范围在requiredChecks加入candidateComparisonCheck：

- contextStateSha256、intentEvidence及scope：绑定当前方案、原需求和比较范围。
- allowedChangedIds、preservedFields：限定候选能改变的对象，至少保留walls、doorStyles、rooms、style；无关房间不能作为自由调整区。
- candidates：每项含id、snapshot（文件/hash）、stateSha256；必须引用真实方案状态，命名版本不是证据。
- hardChecks固定为required_functions、safe_operation、required_access。每项记录status（pass/fail/unverified）、finding和hash证据；评价的是明确声明的模型/产品/现场范围，不是用模型通过冒充现场安全验收。
- dimensions覆盖function、space_use、convenience、safety_comfort、maintenance、visual_coherence。每项有status（assessed/unverified/not_applicable）、benefit、limitation、evidence。必须同时说明收益与代价/未变/未知，不能只填“无碰撞”。
- selection：candidateId必须对应当前被复核的方案；reason解释选择依据；alternatives为每个未选方案说明reason及preferredDimensions；tradeoffs逐项记录dimension、cost和response。不输出自动综合分，不声称最优。
- selection.useConditionScenarioIds引用原operationMatrix中预期受阻的状态，避免选择理由忽略“关门才能取物”等限制；继续复用原交付披露证据，不复制另一套操作规则。额外条件可在conditions里引用text及artifact，代码检查条件文字确实在交付说明中。

代码核对记录完整、真实方案hash、范围、硬条件及取舍披露；六维判断仍由审阅者基于证据作出，不能自动证明美观、舒适或维护耐久。缺记录报告not_provided，新任务声明必需后缺项阻断；既有兼容不代表已做过候选比较。

## 回归

`scripts/test_layout_candidate_review.py` 覆盖：只有碰撞结果、只有一个或重复候选、漂亮/大容量抵消硬条件失败、硬条件未知冒充通过、缺代价/未选理由、越界改房间、陈旧方案、条件未披露、选择忽略受阻状态，以及设计比较只有一个可行候选。合成数据不使用真实户型尺寸或专用柜体实现。
