# 视频前的镜头预演确认（硬门槛）

这是四阶段中的第②步，前提是第①步空间路线已获用户确认（`unified-tour-production.md`）。本文 `homeowner-route-approval/1` 是历史schema名，含义为镜头预演确认；它不能替代路线确认，路线确认也不能替代它。没有路线链的预演不能捕获。

先展示并确认动线动画，再制作任何三维视频。文字参观顺序、静态路线图、碰撞通过、用户同意“生成视频”，都不能代替这一步。此门槛同样适用于低清预览、局部转场样片和直接调用浏览器捕获；`--preview`、`--range` 不得绕过。也不得另写截图帧循环、将 tour 改写成 views 或手工拼接编码来规避确认。

## 必须展示的动画

复用 `assets/h5/tour/rehearsal-template.html` 的已确认版式：家具平面底图居左、参观顺序和时间分配居右、播放和时间轴在底部。生成的是一个离线 HTML，内嵌 PNG 底图及交互图层，不另外交付 SVG 路线图。不要复制参考案例的户型、坐标或时长。

- 当前已确认家具平面底图及完整路径，移动箭头与相机位置。
- 相机独立朝向、中心视线和按墙体截断的视野扇形；朝向必须来自成片同一份逐帧数据，不能用路径切线代替镜头朝向。
- 实际秒数、总时长、拖动时间轴、播放/暂停/重播、0.5×/1×/2×。以 1× 审阅真实节奏。
- 参观顺序与到达时间，当前章节高亮；逐房间观看时间，进入、转出、连接、折返时间另计。
- 总观看时间、连接占比、累计转头和覆盖率只留内部JSON诊断；不在页面显示技术统计卡。数值不能授予舒适度通过。

二维墙体截断并不证明三维可见性；后续仍需网格/主体审计和动态样片审阅。

## 时长与节奏先于全片

先为当前案例提出紧凑的目标总时长/范围，并把具体上限写进预演。按主要空间的有效观看内容分配，不逐件盘点家具，不为覆盖所有角落深进、绕圈或重复扫视。小房间默认稍入后短看；相邻区域代看需明确 observationRegionId 与 adjacentViewReason。进入、观察、退出必须分开计时；观察窗口不包括慢慢转向出口的时间。

同时审阅路径和视线：过长连接、重复折返、持续朝墙、提前盯门垛、连续同向转头，优先通过站位、访问顺序、减少深入和次要观看目标解决。保留真实必需的回程，绝不穿墙制造捷径。

超出案例预算时停止视频捕获：重排路径/视线/目标，再生成新预演。不要以安全阈值通过为理由自动延长总片，不把旧案例的56/57秒设为通用硬指标，也不强行提高步速/转速去塞入时长。确实需要延长时，展示新时长与具体原因并由用户确认新的动画。

## 生成与确认

使用已有 Python 与 PNG 家具底图。`--bounds X Y WIDTH HEIGHT` 是完整 PNG 画布在当前模型毫米坐标中的边界（含图纸边距），须从当前底图的导出坐标取得，不能复制参考户型值。runtime 必须由同一 bundle prepare。

```text
python scripts/production/route_rehearsal.py --tour TOUR --config CAMERA_CONFIG --bundle BUNDLE --runtime RUNTIME --plan APPROVED_FURNITURE_PNG --bounds X Y WIDTH HEIGHT --budget-seconds CASE_MAX_SECONDS --out NEW_REHEARSAL_DIR
```

输出 `index.html`、`timing.json`、`rehearsal.json`、`route-review.pending.json`。打开动画并检查底图映射、路径、相机、视野、时间轴和章节。向用户展示这个确切页面后，一次确认走位、朝向、时长与节奏。只在用户明确接受已展示的动画时，另存 approved review：

- schema `homeowner-route-approval/1`，status `approved`；
- `approvalSource: explicit_user_confirmation`，真实 `confirmedBy` 和原话 `evidence`；
- `presentedAnimationSha256` 指向实际已展示动画的哈希；
- `animationViewed`、`pathAndFacingApproved`、`durationAndRhythmApproved` 都确认后才设 true。

模板默认 pending/false。内部审阅不能代签用户；不添加假用户按钮或让页面点击自动授予确认。记录对话授权由执行者如实绑定，不声称哈希检查能验证人的行为。

批准绑定具体动画、底图、bundle、镜头配置、逐帧路线及时间分配。朝向、路径、视野、机位高度、时长、观看预算或材质/几何改变后重做预演并确认；仅输出分辨率改变可沿用同一预演批准。变更不得继承旧批准。旧案例记录和单纯文字路线批准不能直接升级成动态预演通过。

```text
python scripts/production/h5.py capture --runtime RUNTIME --tour TOUR --out NEW_CAPTURE --full --preview --route-review APPROVED_ROUTE_REVIEW --node NODE --playwright-module PLAYWRIGHT --browser CHROME
```

批准之后依次做网格与主体检查、风险转场样片、完整低成本动态预览、需要时正式/高清捕获。正式/高清还必须提供独立 `--preview-review`，其中 `approvalSource: explicit_user_confirmation`、`confirmedBy`、`evidence` 记录用户确认，`reviewedBy` 与工程审计不能代替；二维预演确认不代替后续三维观看与成片验收。生成后检查实际时长是否仍等于预演，不能在渲染阶段另造路径或拉长节奏。

观察点默认每房一个、最多两个；第二点需要理由。单点最终时长上限3秒，同时位置/朝向静止上限0.5秒；与每房进出总预算同时校验。家具目标和避障路径点不另算停留，禁止逐件停点。

## 当前规则执行版本

以 `tour-rule-implementation.md` 为统一口径。捕获还要求同源 `screenAudit` 与真实连续
播放的 `visualReview`，绑定当前配置、路线、几何及引擎指纹。抽样截图不得填完整连续
播放已通过。新的视觉失败优先于旧数值通过；重绑后用户批准重置pending。

## 明确授权的评审片

用户看过当前预演、获知具体问题并明确要求先出评审片时，可使用
`--review-release RELEASE_JSON --preview --full`。这不是正式/高清交付，也不将失败审计改成通过。
普通捕获继续执行上面的门槛；禁止用临时复制捕获脚本代替本入口。

案例记录 schema 为 `homeowner-review-capture-release/2`，必填：

- `status: authorized_review_capture_only`、`scope: review_video_only`；
- 真实 `userInstruction`、`authorizedBy: explicit_user_confirmation`、`authorizationEvidence`；
- 当前 `ruleFingerprint`；`references` 中 `routeReview`、`renderer`、`clearanceAudit` 的 `{path,sha256}`；
- `allowedScreenIssues` 是当前屏幕审计中每个获准保留问题的完整对象，含精确时间范围；数量不设共享默认值。空列表只适用于没有屏幕问题的审计；
- 若用户也允许连续审阅暂缺，记录 `allowPendingContinuousReview: true`；不能把已失败的连续审阅改成 pending；
- `humanAcceptance: pending`、`productionAccepted: false`，仅描述即将生成的新片。

`routeReview` 仍须绑定已展示动画、走位、朝向与时间的明确确认。网格碰撞/错误、数值契约、
覆盖、房间预算和主体可读性不能豁免；新问题、改动后的来源或不匹配的已知问题清单会阻止捕获。
`clearanceAudit` 使用当前 runtime/tour 的 `h5.py audit` 输出，须包含 scene/geometry/renderer/tour 哈希。
仅允许最高 1280×720 的整段评审捕获，不接受 `--range`。旧的案例专用 /1 记录不自动升级。
Python 与直接浏览器入口调用同一校验器；普通生产入口及最终成片验收保持独立。


四阶段页签与媒体同步按 `tour-presentation-pages.md`：路线页保留开始/结束节点，第二步实时三维预演，装修视频与讲解页右侧为同步大幅路线图。首阶段不混入视频或默认三维播放器；真实三维审阅仍为独立必要证据。
