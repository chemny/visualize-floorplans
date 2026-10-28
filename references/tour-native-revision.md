# 原生导览修订与阶段收口

标准入口为 `scripts/production/h5.py plan-tour --job JOB --out NEW_DIRECTORY`。
本流程只规划、验证及生成审阅页面；视频仍走原有确切路线与实际播放批准关卡。

## 门洞构图在生成阶段参与比较

`tour_doorway.py` 从真实墙体开口与逐帧轨迹的相交关系识别经过的门洞，检查接近期间
视线是否穿过孔径、与门洞中心的偏差及近墙情况。它是可配置的软构图分数，不能抵消
碰撞、倒走、速度/加速度、设施遗漏或重复扫视等失败，也不要求所有门洞永远居中。
没有实际穿越的开口不制造通路；门扇、把手和柜体继续参与真实身体避障。

标准规划入口在硬问题为空时也可对不良门洞构图提出有限修订：局部朝向、同一连接段
去掉冗余摆头、同一连接段的小幅侧移与朝向联动。用公共角度/位置投影维持既有运动
上限、端点和观看窗口；不可连接或不收敛就拒绝，不把当前案例的角度或坐标写成默认值。
修订沿真实通路连续衔接机位和视线，正常行走面向行进方向。

每个候选交同一个最终帧契约和真实网格检查。已有重复扫视模块继续区分连续首次揭示、
顺路再入镜和真正反向重扫；门洞评分不能掩盖新的重复扫视。

## 显式冻结已经通过的片段

已确认方案只修指定连接时，job 增加：

```json
{
  "revisionScope": {
    "chapters": ["当前配置里的连接章名称"],
    "axes": ["pointMm", "yawRadians"],
    "preserveViewingWindows": true
  },
  "search": {
    "maximumRounds": 2,
    "maximumDoorwayCandidates": 3,
    "strictRepairRounds": true
  }
}
```

章名称必须存在且为 transit。观察窗口包含两端帧，逐值冻结；未授权轴和连接章以外
的帧也逐值冻结。首尾位置不移动，退场末帧朝向可在授权轴内修订。时长、帧数、访问
标记及配置保持；候选越界一帧也拒绝。`connectionOnly` 不能替代这个冻结契约。

未给 revisionScope 的新规划允许正常选择观察点、配置镜头和分配案例时间，仍遵守
用户时间锁和观看下限。不能把局部修订的冻结约束误加给所有新规划。

## 一个预算内结束

门洞候选共用 `maximumRounds`、`maximumFullEvaluations`、
`maximumCandidateMeshEvaluations` 和 `maximumPlanningSeconds`。
默认有界修正，不在严格轮数结束后再追加全局细调或递归网格修正。
最终选定结果有硬失败、证据缺失或执行超时时，阶段结论为 `failed` / `action_required`，写明原因。
候选配额用完且所有候选被拒绝或没有改善时，可以保留完成检查的合格基线，并明确记录
`baseline_retained`；不继续无限验证，也不自动改松门槛。

## 同源前后对照

正常呈现分支自动生成 `revision-review/index.html`。同一模型的两个画面按相同绝对
时间播放、暂停和拖动；可定位改动时点。两份轨迹、配置、场景和页面都有来源绑定。
只有实际检查过的图像或播放记录才算视觉证据，JSON/网格通过不冒充看过动画。
`searchOnly:true` 仍仅输出数据和报告，不生成对照HTML或复制runtime。

`tour_revision_review.build_revision_review` 也可供其他工具创建同源对照；不同布局、
过期网格、未绑定的实际播放记录都不能继承为新方案验收。

## 固定收口清单与明确阶段结果

`closeout-report.json` 统一汇总：

1. 主要功能与布局可辨认：核心设施与真实网格可读性。
2. 有序扫视：单次房间介绍、正式扫视方向和重复检查。
3. 正常导航：路径、向前行走与转动约束；数值合格仍需实际观看判断自然感。
4. 无持续遮挡：全片真实网格屏幕审计。
5. 时间在预算内；局部修订还要证明窗口外、观看时长和配置未变。

`engineeringStatus: pass` 表示上述工程检查完成；缺证据为 `action_required`，明确失败为
`failed`。人工播放、舒适度及用户确认单独记录，工程pass不代签用户接受。
内部 `searchOnly` 即使没有页面，也会返回这个确定的工程结果，CLI据此给出退出状态。

`closeout-report.json` 和 `search-report.json` 同时记录 `revisionOutcome`。
`baseline_retained` 表示没有选中可接受的改进，不能汇报问题已修好；`selected_revision`
表示选中了候选，仍不代表视觉改善已经验收。工程通过只证明最终选定结果通过工程检查。

正常速度观看能理解布局，且没有明显重复、突兀转向或持续遮挡后即可结束当前阶段。
短暂经过门框或墙角不直接等同整片失败。已知室外未建模等边界如实保留；不得通过
省略真实报告、遮住室内失败画面或补造外景取得通过。

实现与反例测试：`tour_doorway.py` / `test_tour_doorway.py`，
`tour_pipeline.py` / `test_tour_pipeline.py`，`tour_revision_review.py` /
`scripts/test_tour_revision_review.py`。案例坐标、具体帧段、风格、秒数和用户批准仍留在案例中。
