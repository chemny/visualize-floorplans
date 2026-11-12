# Changelog

## 0.2.14 — 发布候选

- 新增 `compare_render_quality.py`（同帧相似度/峰值信噪比与放大对比图）和 `blender-quality-fast-template.json`（32 采样显卡降噪的质量档），带测试。
- 新增 `references/tour-production-playbook.md`（四阶段流程、门槛、Blender 与远程渲染的做法和坑）；重写 `tour-camera-options-and-lessons.md`（按主题整理、状态列、1 号定稿设置、遗留）；`validate-corpus` 对输入缺失或方案哈希不符的案例标为跳过而不是失败或用错版本，清单支持 `entranceOpeningId`；远程快照回归断言。
- Blender 质量配置新增 `persistentData`、`pngCompression`；新增 `references/blender-render-speed.md`：每帧耗时构成（光追约 3.1 秒、CPU 降噪约 1.5 秒）与对比实验，32 采样加显卡降噪每帧 1.65 秒（原 4.8 秒），仅在 1 号户型验证。整片校验改为按文件比较路径（Windows 路径风格）；远程快照补上灯光检查资源。
- Blender 灯光：新增 `blender_lighting_profile.py`（校验灯光配置键、按灯具编号 > 类型 > 全局取功率、亮度参考带）和 `references/blender-lighting.md`；`import_blender` 支持 `fixtureWattsByType`、`fixtureWattsById`、`cameraBackgroundColor`。远程快照补上 `renovation-components-v12.js`，否则远程灯光检查导入失败。
- 预演生成时把 `tourSha256`、`configSha256`、`bundleSha256`、`schemeSha256` 写进数值报告，评审片授权（`--review-release`）核对这些绑定；此前只有测试夹具会手写，真实流水线产出过不了授权。半帧内的停留差视为取整，不再报 `viewing_time_compressed`；引擎内写死的连接占比 55% 同步改为 80%。
- 持续倒走上限由 0.5 秒改为 1.0 秒（用户于 2026-11-02 决定；依据仅 1 号户型实测 0.58、0.83 秒）。
- 连接占比默认上限由 55% 改为 80%：三个真实户型的整屋参观实测 74% 到 76%，原值在整屋参观里普遍不可达；用户于 2026-11-02 决定调整。案例仍可在 `choreographyPolicy` 中写得更严，高于 80% 须写 `choreography_limit_override` 例外。
- `brief-from-route` 现在会把小空间（单门、6 平方米以内、非入户首个房间）的站位移到门内 400 毫米，使 `small_room_too_deep` 在三个户型上都不再触发。
- 镜头诊断新增 `roomWobble`（房间内左右回摆）、`wallFacingRuns`（近墙连续段）、`timeBreakdown`；选项 `sweepConsistencyWeight`、`turnInsideSmallRoom`；brief 支持 `motionReviewLimits`（本案转头速度上限，须有 `motion_limit_override` 例外）。均默认关闭，仅在 1 号户型上验证。
- 节奏与小空间：默认巡航 1.1/窄处 0.95 米/秒；新增终段加速度限制 `tour_workflow.limit_acceleration`（转头限速、窄处限速造成的速度台阶一并抹平，消除 `path_tangent_discontinuity`）；新增 `tour_small_room_depth.py` 与 brief 选项 `navigationPolicy.smallRoomShallowMm`（6 平方米以内单门小空间不进门内超过设定深度，入户首个房间除外，违反记 `small_room_too_deep`）；预览页诊断预演不再标“待审阅”。
- 速度与贴墙：路径舒适净空偏好（不绕路、不降低硬安全距离）、分档巡航、缓停缓起、`abrupt_stop` 检查；全部默认关闭，本案实测总时长 72 → 约 93 秒。
- 连接段转头新增相对上限：镜头转头不得比路线自身转弯多出 90° 以上（`transit_turn_beyond_path`），绝对 180° 不变；诊断与回归基线同步。
- 新增 `h5.py tour-draft`（秒级镜头草稿）、`optimize-stations`（站位按网格画面选并复核撤销）、`validate-corpus`（案例一键跑完整前半链并与基线比较）、`record-approval --kind camera|video`（镜头预演、整片视频确认记录，拒绝代理名称与未完成的预演）。修复 `test_tour_rules` 里早于“加大净空重试”的过期测试桩。
- 新增 `h5.py brief-from-route`：按已批准路线生成镜头 brief 与假设清单（总时长、覆盖百分比、视高原因必须由案例给出）；子房间站位超过两个时归入相邻房间；扫视装不下全部主体时保留主体并报告。
- 新增 `h5.py record-route-approval`（只接受用户姓名与原话）、镜头 brief 模板、开跑前的 brief 与路线对齐检查、`camera-diagnostics.json` 按章节诊断。
- 镜头阶段新增默认关闭的选项：最少转头连接规划、联合扫视选择、小房间回退（12平米以内、单出口、1.2米/2.5秒）、按主体的俯仰与可降低的视高；修正转头多转一整圈、候选对照版不对等、画面检查预算不足。只在一个户型上调试过，详见 `references/tour-camera-options-and-lessons.md`。
- 参观制作拆为独立四阶段：新增 `h5.py plan-route`、`tour-stage-status`；镜头、捕获入口须消费用户路线确认。旧预演和旧确认无路线链，不能捕获；门槛源码变化也使旧规则指纹失效。

- 平面桌椅遮挡按座面与台面层次绘制，标签沿用相同顺序；不修改家具高度或三维几何。加入原生SVG像素、实际选中与旋转合成户型回归，避免收在桌下的座面显示到桌面上。

- 增加历史案例副本迁移与同源展示素材检查入口 `case-upgrade-check`；旧概念图/视频单列来源，不继承验收。补齐明确外围饰面带的独立保留和缺口区域报告，统一实际墙端/门洞地面检查；门把手按实际高度排除点位误报，浏览器地面与风格回归适配独立连接带和不同房间编号。

- 固定四步参观流程，默认H5与可选Blender共用路线确认及具体视频批准；Blender短样、整片、远程执行入口均复查同一份路线证据。
- 补齐远程设备、冻结输入、恢复、远端编码与回传；未改JSON保持原字节，中文报告使用UTF-8。
- 补齐局部时序诊断、显式采样降噪配置、可选无扩散放大短样及最终音画/页面绑定检查。
- 区分普通、Blender API及浏览器回归，移除本机路径依赖；按功能检测可选运行环境，不自动安装。
- 整理安装链接、双渲染使用说明及版本边界。当前用户场景、路线和媒体不迁移、不改写。

## 0.2.11 — 本地未发布

- 阶段收尾：完整音轨/字幕/参数追溯、统一全部模块回归收集、独立子系统版本说明与本地固化边界；保留案例用户验收待审。
- 收尾回归修正：旧隔离夹具接入地板/灯具预处理，把手纳入碰撞断言；几何测试显式复用已有依赖，跨户型指针测试先适配视图，保持真实点击及拖拽要求。CI 覆盖全部生产 Python 测试。

- 补齐路线确认→视频审阅→讲解制作的执行关卡；新增绑定具体视频与路线的待确认记录。
- 新增 narration-prepare/compose；页面包装同步检查视频确认，样例仅演示，不授予制作批准。
- 增加越级拦截、确认失效及实际短媒体合成回归；不修改现有案例，不自动批准或发布。

- Local 0.2.10: consolidate the review presentation SOP and traceability matrix; enforce top-level navigation, sidebar chapter ownership and explicit empty-media states; verify regeneration from the public CLI without changing case data.
- Local 0.2.9: merge media route and room chapters into a synchronized map/list sidebar; remove expansion dialog and duplicate chapters; bind module URLs to content hashes to avoid stale UI code.
- Local 0.2.9: use 16:9 media boxes with independently sized route panels; phrase-based, punctuation-light subtitles with bounded estimated timing and stable DOM updates; remove route-page auxiliary/sample controls.
- Local 0.2.9:  lock the three-stage presentation SOP, isolate the pure route map from stage navigation, add an auxiliary 3D preview entry and reject nested full-page review layouts during generation. No route, scene or media changes.

## 0.2.4 · timed route rehearsal gate · 2026-10-22

- Restore reusable plan-based animation with moving camera, independent gaze/FOV, arrivals, viewing/transit timing, playback and scrub controls.
- Require explicit displayed-animation approval before every tour capture in Python and the direct browser adapter, including low-resolution previews and ranges.
- Bind approval to the exact route, heading, timing and source artifacts; block over-budget routes and preserve pending user/visual states.

## Unreleased

- Local 0.2.8: connect real-opening doorway composition diagnostics and bounded joint position/gaze candidates to `plan-tour`; add explicit revision scopes that freeze approved observations and all undeclared frame fields. Generate hash-bound synchronous before/after pages and conclusive engineering closeout reports, separate from playback/user acceptance. Share candidate/deadline/mesh budgets, preserve hard gates, and reject stale target-binding evidence. Read `revisionOutcome`: baseline retention is not a successful repair. No current-case update, video capture or publication is implied.

- Generate the shared three-stage tour interface from the production planner: route-only start-to-end animation, video review with a large synchronized route map, and narration with independent sound/caption controls. Add relocatable media/hash/timebase binding, pending placeholders, explicit post-encode integration and independent-layout/mismatch regressions. Keep actual 3D preview and all approval gates separate.


- Local 0.2.7: unify room-aware wall finishes, aligned moulding/panel patterns and existing artwork by style. Create follow records for actual interior wall faces; protect fixed choices, wet/service rooms and furniture/door geometry. Add procedural art palettes, fixed/follow controls, persistence and scope regressions.

- Local 0.2.6: add classic glass-arm crystal main fixture with bead swags and pendants; preserve existing three options, fixed-choice behavior and light parameters. Validate body bounds and expand repeated mesh instances in production export. Wall-decoration audit does not change finishes.

- Local 0.2.5: style-bound flat/convex/crystal main fixtures with room adaptation, fixed-choice overrides, matching plan/mesh fields, ceiling/source-offset preservation and low-ceiling validation. Preserve other fixture types and scheme layouts; add policy/geometry regressions and actual-page persistence checks. Not published.

- Organize existing placement principles into six evaluation dimensions and extend the existing layout gate with evidence-bound candidate comparison, hard constraints and explicit trade-offs. Distinguish prospective comparison from retrospective validation; do not imply layout optimality from collision clearance.

- Extend the existing layout review gate with assembly function intent, explicit door/cabinet/person operating-state combinations and hash-bound final plan/mesh/screenshot receipts. Report legacy omissions and conditional usability honestly; add regression counterexamples without importing case cabinet dimensions or rendering code.

- Restore sliding-door leaf count, wall-relative stacking direction and opening-percentage controls in the effective property panel. Share panel geometry across plan/mesh/net-opening reports and parity-check Python route obstacles; retain protected apertures. Add synthetic browser edit/mesh/undo/persistence and cross-language regressions.

- New-floorplan regression: accept exact room-owned short skirting returns during state validation while retaining ordinary furniture size bounds; rebuild the shared engine and add a size regression to local smoke checks.

- Close workflow-review gaps without changing existing cases: require explicit image inventory/framing evidence, distinguish label-only revisions from redesign, and exercise existing source/layout/style binding gates in installed-source regression.
- Replace the case-specific two-issue review-capture release with `/2`: exact displayed-animation authorization and issue list, current source/renderer/clearance evidence, low-resolution review-only status, and one validator shared by Python and browser entries. Ordinary capture and formal acceptance remain strict.
- Include review-release, dynamic-preview and screen-quality Node checks in local regression; no publication or automatic case migration.

- Add data-only room-first fragment qualification, shared-scene batch mesh checks, evidence-bound fragment connection selection and explicit frame/second deficit reports. Preserve every viewing lock and revalidate the assembled whole route.
- Remove artificial per-vertex connection waits: curve subdivision does not add physical travel time. Share density-independent walking/yaw/pitch work between candidate connection pricing and timeline reconstruction.

- Connect exact tour endpoints only to reachable grid cells, rejecting blocked endpoints rather than snapping through walls or door leaves. Add bounded, case-configured passage-coverage gaze proposals and honor per-chapter navigation policy even when endpoints are unchanged; final timing, coverage, motion and mesh gates remain mandatory.

- Certify final gaze-projection feasibility, reject duplicate seed station proposals before beam/local selection, and accept bounded case station, entry-framing and safe rounded connection-waypoint candidates without altering timing locks.

- Repair tour candidate evidence parity: numeric failures still receive bounded mesh checks; untested candidates and historical visual failures cannot win by dropping checks or changing floats.
- Include continuous moving views in joint/local repair, preserve shared poses and viewing frame locks, screen connection budgets early, and repair positional/velocity seams with collision checks.
- Search pitch in both directions using projected object bounds, propose an actual entrance closing view, reserve mesh budget across repair rounds, and add data-only `searchOnly` validation without new rehearsal pages.

- Add `homeowner-tour-rules/2`: one camera profile, final-frame trajectory continuity, mandatory intents/visit budgets, scoped exceptions and exact timing locks; block silent sharp-corner fallback.
- Count coverage within the first continuous visit; audit full-timeline mesh screen occlusion, clipped/brief subject composition, approach reversals and empty endings. Compare feasible candidates using the same evidence.
- Bind current engine fingerprints and real continuous-playback review to both capture gates; pending, sampled or failed visual reviews cannot be promoted by numeric success. Existing preview data and accepted historical media remain untouched.

- Consolidate homeowner touring into `references/tour-planning-contract.md` and a final-frame contract shared by design, revisions, rehearsal, Python capture and the direct browser capture report gate.
- Require case-specific coverage and total-duration policies; remove obsolete split-room viewing guidance and case-specific room budgets from shared instructions.
- Preserve per-window viewing floors across revisions; check real-room continuity, sweep direction, station counts, exact entrance return, geometry, motion, coverage and complete visit budgets independently.
- Add synthetic cross-case and Python/JavaScript gate regressions; numeric success keeps actual 3D visibility, dynamic comfort and human acceptance pending.

- Add scoped connection refinement and optional short moving observation windows with per-chapter viewing-frame preservation, exact endpoint connectivity checks and unchanged motion ceilings; retain fresh coverage, budget and visual-review gates.

- Enforce one default / two maximum observation stations per real room, second-station justification, final per-station duration and simultaneous stillness checks in tour design, rehearsal and capture gates. Furniture targets and navigation vertices do not create extra stops.

- Rename display name, Skill directory, invocation identifier, archive root and active repository links to Interior Design / interior-design (家装助手); preserve historical accepted case bytes.

- Inspect large JSON dependency documents one at a time with decoded-string indexing; fail closed on malformed or duplicate keys instead of skipping oversized bundles.

- Add stage-bound media cleanup planning with explicit inventories and conservative reference protection.
- Require hash-bound batch authorization, verified backup outside the project and reversible quarantine; provide collision-safe restore.
- Keep scheduling and permanent deletion out of scope. Existing projects are not cleaned automatically.

## 0.2.2 · homeowner tour methods · 2026-10-08

- Reuse subject-key gaze curves, effort-based timing and bounded local corrections.
- Require hash-bound dynamic preview reviews before production capture; separate technical checks from human acceptance.
- Clarify shallow room visits, doorway turns, local gaze/pitch scope and tour closeout checks.
- Include a second accepted 57-second tour example with explicit review boundaries.

## 0.2.1 · layout and workbench editing · 2026-10-07

- Add editable wall art to a distinct decor catalog and keep it visible in
  furniture layout and 3D instead of treating it as a construction detail.
- Require an isolated current-scheme HTML export and actual save/reload and
  download/reopen checks for portable editable delivery.

- Add optional loopback project persistence and stage-bound Confirm and continue,
  with atomic save, previous snapshot, stale-tab conflicts and bounded Agent waits.

- Require displayed style comparisons before undecided-user selection; gate both
  host and legacy paths with file-bound evidence and explicit fallback waivers.

- Generalize bed sizing, wall/corner storage, curtain allowances and optional entry storage.
- Add reviewed predecessor migration and portable current-scheme export; preserve browser save semantics.
- Provide concise object actions, Copy and 2D context insertion with explicit library opening.
- Compact the furniture pane across desktop and narrow windows.
- Use integer exterior dimension labels, one font size and total-preserving short-span merging.
- Technical regression checks do not certify browser visual acceptance or source dimension closure.

### Guided user workflow

- Use everyday living convenience as the default; replace abstract priority
  ranking with optional concrete special needs and respect no extra requirements.

- Start from one floor-plan image; furniture and style references are optional.
- Consolidate input/design decisions into plan and needs, furniture/functions,
  and style/output scope; keep final output acceptance separate.
- Continue authorized drafting and self-checks between concentrated question
  batches, offering recommendations and reusing unchanged approvals.
- Show six default styles in one eye-level interior comparison through host tools; retain the legacy
  4/8/12-option planner contract without changing runtime behavior.


## 0.2.0 · version label update · 2026-10-06

- Remove the beta suffix from the current Skill, workbench and package version identity.
- Rebuild the final reference workbench; no geometry, lighting or feature changes.
- Historical beta records and unverified platform/visual scopes remain explicit.

## 0.2.0-beta.5 · workbench reliability and presentation · 2026-10-06

- Follow-up: apply thin-TV legacy defaults across styles rather than only the
  reference case. Ceiling diffuser emission, fixed lighting, native resolution
  and presentation cuts already share common implementations.

- Follow-up: champagne style revision 6 removes warm wood-grain cabinet
  finishes in favor of champagne lacquer or pearl white. Apply approved case
  living/dining/entrance marble and cabinet colors once to cached schemes.

- Follow-up: add independent dining/coffee tabletop accessories and scoped
  kitchen-corner decor. Preserve body-height normalization, picking and walk
  footprint; batch opaque accessory surfaces separately. Kitchen fixtures and
  working space remain authoritative for placement.

- Follow-up: add subtle champagne upholstery/headboards and partial cabinet
  fronts; retain pearl base, plain floors and lighting. Later revision 6 replaces wood finishes.
  Silver metallic fridge finish uses fine brushed relief; TV depth is 35 mm.
  Upgrade untouched champagne defaults while preserving custom palette choices.

- Follow-up: presentation cut clips architecture, doors/windows and opening
  trims only; keep complete furniture to prioritize layout/decoration. Preserve
  closed architectural caps, fixed lights, picking and full-height/walk restore.

- Follow-up: render wall cuts as unlit black; round/square/panel ceiling
  diffusers emit on their side faces and use omnidirectional fixed illumination.
  Preserve fixture envelopes, group budgets and native pixel ratio.

- Follow-up: remove adaptive render-resolution reductions and the DPR2 cap.
  Render at native display pixel ratio during idle/motion/high frame cost.
  Retain batching, on-change rendering and fixed light groups.

- Test furniture collision against standing-body height instead of ignoring all
  furniture mounted above 1100 mm.
- Merge plain opaque static parts within one furniture body/material; preserve
  actual triangle surfaces, dimensions, picking and production export.
- Render camera/scene changes immediately; skip repeated GPU and label rendering
  when idle, and cache unchanged shadow maps.
- Add fixed, capped indoor-shadow trials independent of viewpoint. Keep them
  disabled by default pending case-specific visual review; no new UI toggle.
- Extend synthetic collision, dimension, shadow-budget and idle-render checks.
- Rebuild the reference workbench while preserving scheme, original inputs,
  selected AI images and older media bytes. Media re-export deferred by user.
- Consolidate reusable rendering, persistence and floor-connection safeguards in
  `references/workbench-reliability-rules.md`; retain case-specific choices in case data.
- Isolate independent HTML export caches; restore edits after refresh.
- Add validated finish-only connection patches with synchronized 2D/3D and
  production export; report their areas without changing room boundaries.
- Reduce uniform lighting fill and night amplification; the example uses one
  fixed 512-pixel dining-shadow trial and local ceiling presentation compensation.
- Published technical evidence remains distinct from fresh case visual acceptance.

## 0.2.0-beta.4 · local workbench stabilization · 2026-10-06

- Added shared version identity in HTML/build evidence and a matching local archive.
- Added room-area pending detection after wall geometry changes, with undo restoration;
  original room polygons remain authoritative until a new layout is confirmed.
- Added non-mutating main-light coverage, room assignment and finished-ceiling warnings.
- Made marble veins case-configurable in SVG and Canvas; bind material presentation
  to style approval scopes and production exports.
- Extracted storage, pointer-lock diagnostics, material presentation, label anchors,
  room-area status and permanent lighting rig into tested modules.
- Added reusable unit/browser fixtures for rectangle, concave and nine-room stress
  cases; storage, export/reopen, joystick, keyboard and refusal fallback checks.
- Corrected verification API wall toggling to use the same implementation as the UI.
- Remains local only; embedded native permission, Windows and physical mobile
  checks do not inherit desktop/synthetic acceptance.

## Historical local interaction refinement · 2026-10-06

- Simplified walk to a full-width scene with compact on-demand controls,
  removing room jumps, duplicate sidebars/HUD and entry/resume modals.
- Restored desktop/touch joystick and drag/keyboard defaults; native pointer
  lock is optional, with automatic nonblocking fallback on rejection.
- Replaced two-line room cards with compact single-line annotations, progressive
  zoom-out detail and measured overlap handling.
- Added optional imported-case preservation for explicit bed model choices and
  unchanged window trim dimensions. No apartment data is embedded in the engine.
- Rebuilt the local engine. The existing beta.3 installation archive and release
  validation describe the prior snapshot; no archive or remote release is updated
  by this local UI revision. New UI acceptance remains pending user review.

## 0.2.0-beta.3 · release preparation · 2026-10-06

- Added optional explicit camera observation cues, bounded smooth turning, and
  validation of timing, target coordinates and rotation limits. Camera intent
  remains separate from actual sustained-subject visibility.
- Re-ran real-model observation diagnostics without changing the declared
  visibility thresholds; timing and review evidence remain case-local.
- Updated bilingual agent installation, capability and platform boundaries.
- Verified and bundled the reference workbench's current upstream MIT notice,
  retaining source and license revision attribution alongside Three.js notices.
- Made production/source interpretation JSON encoding explicitly UTF-8 and
  added a Unicode/space-path CLI regression.
- Rebuilt distributable source archive and exercised clean-directory checks.
  Different-floorplan, cross-host runtime and Seedance verification remain deferred.

## 0.2.0-beta.2 · local quality gates · 2026-10-06

- Added independent technical, geometry, visual and human-acceptance states;
  source/image/tour review contracts, case-local template and strict accepted
  handoff/package gates. A preview manifest boolean cannot grant acceptance.
- Added separate image-axis calibration, dimension and geometry provenance,
  critical ambiguity checks and structure-scope binding.
- Bound AI outputs to current H5 reference bytes, exact capture cameras, scheme,
  agreed image sets and recorded per-image/cross-view checks. Native aspect
  rounding is explicit; no image-recognition capability is inferred.
- Added actual-mesh subject visibility/extent and near-wall measurements across
  observation time windows, route/intent binding and current physical envelope.
  Diagnostic previews retain failures; formal camera production rejects them.
- Added targeted negative/positive regressions and same-case window inspection.
  No images or video were regenerated, and no prior accepted case was changed.
  This is a local source update, not a rebuilt installation archive or release.

## Unreleased · fresh verification fixes · 2026-10-05

- Exercised a fresh original-plan-to-H5-to-AI-image-and-H5-video same-case run,
  excluding Seedance and historical generated media/model/camera artifacts.
- Corrected window sill/height handling, wall origin, export readiness, hanging
  fixture anchors, preview route gating, false trim obstacles, sliding panel
  poses, wall end joins, ordered visit binding and tight-corner sampling.
- Added a rejecting luminous-face visibility gate and five route regression tests
  relative to the prior baseline; local regression count is 126.
- Recorded 26 UI checks plus resume/revision/approval gate checks. Visual subject
  probes still identify camera focus/time-allocation limitations; no claim of
  automatic visual approval, cross-floorplan certification or public release.

## 0.2.0-beta.1 · local closeout · 2026-10-05

- Added reusable single-file H5 template, source engine and component models;
  separated case geometry, furniture, fixtures, areas and camera parameters.
- Added `h5.py` build, actual-mesh/drawing export, preparation, camera audit,
  capture/resume, production, handoff and package commands.
- Made H5 the deterministic production default; retained explicit Blender branch.
- Added ceiling/fixture visibility, homeowner motion, dimensional envelopes,
  source-version binding and handoff guidance from the accepted local workflow.
- Updated bilingual README, agent entrypoint, runtime guidance and verification
  status; included Three.js runtime license and reference-code attribution.
- Performed limited syntax/entrypoint/build/package checks. New-floorplan tests,
  full regression and Seedance remain deferred. No remote release was made.

## 0.1.0-beta.1

- Existing floor-plan interpretation, reviewed layout, conceptual-image planning,
  scoped delivery approval and deterministic SVG/PNG tools.

- Local preview: fixed four-light runtime budget with room-aware fades and adaptive pixel ratio; fixture meshes/exported illumination preserved. Performance and visual acceptance remain case-specific.

- Local brightness preview: broad downward runtime fills, view-facing main-light priority, stronger night main lighting and reduced day fill; visual acceptance pending.

- Fix: remove camera-driven light selection. All enabled fixtures now contribute to permanent spatial illumination groups; adaptive resolution remains independent of lamp state. Prior moving-budget previews superseded.

- Remove the global fixture light toggle and its public setter; day/night keeps fixtures enabled. Roof and pointer-lock controls are unchanged pending discussion.

- Local preview: preserve pointer-lock rejection diagnostics, hide refused optional lock control, retain focus retry and fallback controls; synchronize plain marble presentation in 2D/3D.

## Local reference case · 2026-10-06

- Bundle supplied inputs, selected concept images/drawings, current beta.4 workbench and scheme, retained H5 tour and compressed source mesh under assets/reference-cases/jujian-champagne-pearl.
- Add offline index and bilingual discovery links; keep representation differences explicit without retaining intermediate versions or audit history.
- Exclude Finder .DS_Store metadata from local Skill archives. No engine changes or GitHub publication.

## Beta.4 publication preparation · 2026-10-06

- Include the provider-authorized full reference case and preserve original upstream notices. Clarify current demo versus retained media sources.
- Exclude uncurated historical furniture-reference files from distributable archives; keep local originals.
- Fresh macOS source, Python, Node subject and interaction regressions pass. Windows physical/runtime checks remain deferred as agreed.

## Local unified confirmation workflow · 2026-10-06

- Add placement principles covering headboard/entry sightlines, bedside functions, wall anchors and guest states.
- Use one canonical H5 case from the first confirmation round; derive structure/layout drawings from current state.
- Preserve source uncertainty, scoped approvals and reference-case revision boundaries. No GitHub publication.
- Fix furniture labels to distinguish single beds from double beds by width.
- Derive entrance annotations from case openings instead of retained example coordinates.

## Local door and equipment review · 2026-10-07

- Require inward-opening preference, receiving-wall/hinge review and explicit door exceptions.
- Add whole-home essential-equipment inventory with separate 2D/state/mesh checks.
- Case-specific door relocation and equipment additions remain unaccepted design proposals.

### Local layout and editing revision — 2026-10-07

- Require room-level wall-anchor comparison and functional furniture groups before choosing layout coordinates; review daily and guest operating states from the same workbench.
- Separate removable door leaves from locked structural apertures; add direct hinge/swing controls and keep passages after leaf deletion.
- Support full-height partial removal for editable partitions with shared plan/3D/export state, undo and room-area invalidation. Omit demolition traces from the current view.
- Add persistent sidebar Save action with validated success feedback. Browser-local persistence is distinct from design acceptance.

### Local quick-menu and geometry correction — 2026-10-07

- Put door hinge/swing/delete actions and whole-wall removal in the selected-object popup, separate from properties.
- Move Save to top-right navigation; show persisted last-save timestamp in bottom-right status.
- Add review rules for carrier-wall alignment and floor coverage to wall faces; retain source room polygons when explicit finish patches fill edges.

## 0.2.3 — Nine-style selection defaults

- Default catalog and host workflow now use one 3x3 board with nine agreed styles.
- Add per-style generation prompts used by comparison and selected-style tasks; retain historical 4/8/12 planners.
- Add European luxury, French, warm Italian and Paris art workbench palettes; preserve legacy Milan state compatibility.
- Current-case French selection is recorded in the case, not embedded in shared defaults.


## Unreleased — three-round homeowner-tour gap closure

- Ordered frozen-scheme targets now drive generated sweep and final-frame visibility/order evidence.
- Aggregate sweep direction across a real room; exclude ordinary transit, report missing historical room metadata.
- Reject legacy/missing camera-evidence capture reports in Python and JS; disable ungated Blender animation at both entrypoints.
- Check full-timeline sustained wall proximity and angular acceleration; bind production subject-audit samples to required route targets.
- Add failure-injection regressions and a read-only three-case matrix auditor. Historical acceptance is preserved; numeric results never grant playback acceptance.


## Unreleased — unified homeowner planning job

- Add plan-tour job entry with bounded joint station/path/gaze candidates and report-driven local repairs.
- Preserve source schemes and viewing durations; sparse angular constraints are rechecked on final frames.
- Produce synchronized 2D/actual-3D interactive rehearsal and bind the displayed parent page to pending approval.
- Add browser-free actual triangle subject preflight; retain dynamic comfort and human acceptance as pending.
- Anchor coverage time sampling per interval so unrelated earlier timing changes do not shift unchanged observation samples.

### Unreleased — door identity and double-leaf clearance

- Compare hash-bound source observations with effective door model/count/hinges during builds; legacy missing evidence is unverified. Recognition0.3 records independent leaf identity.
- Shared swing geometry checks both double leaves and removed-leaf passages; route planner uses the same geometry. Source fidelity, geometric clearance and functional usability remain distinct.

### Unreleased — executable layout and edit-intent review

- Bind existing room-function, composition/operation and exact-edit checks to the actual scheme version; verify semantic inventory, axes, edge gaps and operating footprints.
- H5 builds recheck attached layout records; legacy missing records explicitly remain unreviewed. Synthetic regression counterexamples cover absent beds, surplus desks, too few seats, split/unequal cabinetry, misalignment, blocked operation, stale evidence and unintended edits. No case geometry or preferences become defaults.
