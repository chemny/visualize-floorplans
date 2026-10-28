# Bundled resource index

Paths below resolve from the Skill root. Consult when selecting a helper script or template.

## Bundled resources

- `scripts/production/tour_pages.py` and `assets/h5/tour/{rehearsal-template,stage-template}.html`: shared route/video/narrated pages. See `references/tour-presentation-pages.md`.


- `scripts/project_service.py`: loopback project save, conflict detection,
  stage-bound confirmation and bounded Agent waits. See `project-save-confirm.md`.

- `scripts/check_style_selection.py`: check case-local visual selection evidence
  before asking for a style choice or starting selected-style production. Read
  `references/style-selection-gate.md`; this does not inspect image semantics.

- `scripts/plan_project.py`: validate a manifest and compile deterministic Image
  2 task prompts without calling an external API.
- `scripts/plan_delivery.py`: compile the client-facing base package, adaptive
  views, semantic camera intents, and a delivery-review template.
- `scripts/delivery_state.py`: bind layout/image acceptance to files, gate
  execution and live review, and permit local handoff without duplicate approval.
- `scripts/validate_delivery.py`: enforce per-image structural checks and
  package-level multi-image consistency before final export.
- `scripts/test_workflow.py`: local regression tests for validation, dependency
  ordering, and structural constraints.
- `scripts/test_interpretation.py`: synthetic input-completion, overlay geometry,
  cross-file authority, and changed-file regression tests.
- `scripts/interpretation_authority.py`: inspect evidence bundles and candidate
  content hashes; does not grant user approval or replace source comparison.
- `scripts/validate_access.py`: validate confirmed room connectivity, swing-door
  direction, and sliding-door metadata without requiring a tour route.
- `scripts/validate_route.py`: reject discontinuous routes and steps that do not
  use confirmed doors or passages.
- `scripts/validate_recognition.py`: reject unsupported doors, windows, bay
  windows, traversable gaps, physical dashed lines, and semantic zones without
  geometry evidence.
- `scripts/render_interpretation.py`: render deterministic access and zoning
  overlays on the fixed 2D base without asking an image model to redraw walls.
- `scripts/render_floorplan.py`: render generic structured wall/access geometry
  to independent SVG elements, then export the exact same revision to PNG.
- `scripts/render_furniture_layout.py`: render reusable top-view furniture
  symbols and reject declared wall, furniture-overlap, and door-swing conflicts.
- `scripts/assemble_contact_sheet.py`: copy complete confirmed image pixels into
  a labelled canvas without cropping, resizing, or generative redraw.
- `scripts/vector_tools.py`: shared validation, geometry, atomic-write, and
  deterministic SVG-to-PNG support for the drawing tools.
- `assets/project-template.json`: copy and fill for a new project.
- `assets/sample-project.json`: runnable sample manifest for dry-run verification.
- `assets/sample-topology.json`: runnable access graph and ordered tour-route
  validation sample.
- `assets/sample-recognition.json`: synthetic recognition-record example for
  local validation; not a user-confirmed production plan.
- `assets/floorplan-input-template.json`, `assets/furniture-layout-input-template.json`,
  and `assets/contact-sheet-input-template.json`: case-neutral structured inputs;
  fill them in a run directory rather than editing the templates in place.

## Example and historical validation resources

- `assets/reference-cases/jujian-champagne-pearl/data`: example scheme and retained media-source metadata.
- `assets/reference-cases/jujian-champagne-pearl/images`: thirteen selected concepts, linked by its case index.
- `assets/reference-cases/jujian-champagne-pearl/licenses`: retained upstream notices.
- `assets/reference-cases/jujian-champagne-pearl/tour`: the retained tour and its route/source records.
- `assets/reference-cases/jujian-champagne-pearl/manifest.json`: per-file purpose and hash index.
- `assets/reference-cases/jujian-champagne-pearl/workbench/index.build.json`: retained example build evidence.
- `assets/renovation-concept-showcase.png`: historical concept illustration.
- `references/beta4-workbench-validation.md`: historical bounded checks, not current acceptance.
- `references/release-validation.md`: current release boundaries and historical evidence.
- `references/local-beta-status.md`: historical technical and visual scope limitations.

## 已确认的第二个导览案例

- `assets/reference-cases/dimensioned-homeowner-tour/index.html`：最终 57 秒场景视频及简要入口。
- 同目录 `README.md`、`manifest.json`、`acceptance.json`：案例边界、文件哈希及明确用户接受记录。
- 只保存最终配置和核验摘要，不包含中间迭代或渲染网格。复用通用方法见 `homeowner-tour-method.md`；具体路径和角度不能当作共享默认值。

## 阶段性素材清理

- `references/stage-cleanup.md`：阶段触发、引用保护、批次确认、备份和恢复边界。
- `assets/cleanup-inventory-template.json`：空白清单，不能代表已确认。
- `scripts/stage_cleanup.py`：scan / apply / restore；无后台或永久删除。
- `scripts/test_stage_cleanup.py`：临时目录内的保护、陈旧计划、备份失败及恢复测试。

- `production/route_rehearsal.py` (under scripts): reusable offline timed route/independent-gaze rehearsal from the approved PNG and exact tour; emits pending approval only.
- `assets/h5/tour/rehearsal-template.html`: plan, animated camera/FOV, sidebar arrival/viewing times, playback/scrub controls; generic extraction from the previously confirmed homeowner page.
- `references/route-rehearsal-gate.md`: explicit displayed-animation approval before any video capture, with case-specific duration budget and invalidation.

## 统一参观规划契约

- `references/tour-planning-contract.md`：顺序、观察窗口、路径、镜头、预算与验收的统一入口。
- `assets/h5/tour/tour-brief-template.json`：无个例坐标、总秒数或覆盖百分比的待填模板。
- `scripts/production/tour_contract.py`：最终帧统一检查及独立审计CLI，不生成视频。
- `scripts/production/refine_tour_connections.py`、`compact_tour_visits.py`：局部连接修订、保留逐窗口观看时长的安全移动观察。
- `scripts/production/test_tour_contract.py`：分次扫房、伪装停点、观看压缩、入口返回、覆盖/预算和证据边界回归。

## 门型与组件能力

- `references/component-use-and-capabilities.md`：用途、组合、可选性及已有检查入口。
- `references/door-selection.md`：门型决策及实现边界。
- `assets/component-capabilities.json`：全注册项按族清单，非逐项运行验收。
- `scripts/check_component_capabilities.py`：清单覆盖、别名及能力边界一致性检查。

- `assets/h5/source/sliding-door.js`：二维、三维、面板净开口统一面板模型。
- `scripts/test_sliding_doors.mjs`、`scripts/production/test_sliding_checks.py`、`scripts/test_sliding_editor.mjs`：跨语言面板几何、通道障碍、真实浏览器编辑/网格与持久化回归。

- `references/layout-use-and-representation-contract.md`、`scripts/layout_use_review.py`：复用布局验收入口的成组意图、条件使用状态、最终输出回执扩展。
- `scripts/test_layout_use_review.py`：状态遗漏、人体受阻、二维覆盖及截图动画时机等回归反例。

- `references/layout-candidate-comparison.md`、`scripts/layout_candidate_review.py`：六维候选比较、硬条件与取舍记录，复用layout_review入口。
- `scripts/test_layout_candidate_review.py`：重复候选、只看碰撞、硬条件被美观抵消及未披露代价等反例。

## Workbench source and browser verification

- `scripts/production/rebuild_h5.mjs`: rebuild the bundled engine and component
  registry using existing dependencies, then write `assets/h5/engine.provenance.json`.
- `scripts/production/engine_provenance.py`: check source/bundle/registry freshness;
  the standard H5 build enforces the same check before output.
- `scripts/workbench_browser_suite.py`: one local build, loopback serve and isolated
  browser regression entry; select `core`, `full` or named checks. Missing browser
  dependencies are reported without installing anything.
- `scripts/browser_artifact_evidence.mjs`: bind browser findings to exact served
  HTML and build engine/template/case fingerprints; reject stale or changed files.
- `scripts/test_workbench_document_contract.py`: prevent reintroduction of obsolete
  UI identity, light-time, shower-menu, wall-selection and floor-area clauses.
- `scripts/workbench_cross_layout.py`: generate and verify independent renamed
  rectangular, concave/rotated and furniture-free fixtures; keep required checks
  and absent capabilities explicit in the matrix report.
- `scripts/production/workbench_regression_cases.py`: synthetic case definitions,
  separate from reference homes and legacy stress fixtures.
- `scripts/test_component_contracts_browser.mjs`: dynamic component selection,
  local-axis pointer resizing and actual SVG/mesh/history/persistence contracts.
- `scripts/test_workbench_cross_layout.py`, `scripts/test_workbench_test_targets.mjs`
  and `scripts/test_component_contract_targets.mjs`: prevent skipped mechanisms,
  fixed reference-case IDs and incorrect rotated resize directions.

## 审核呈现 SOP 与原生入口

- 唯一呈现规范及实现/测试映射：`tour-presentation-pages.md`。
- 生成：`scripts/production/h5.py tour-pages` → `tour_pages.py`；同样接入 plan-tour 与捕获后的正式入口。
- 地图/逐行列表：`assets/h5/tour/route-panel.js`、`tour-media.js`、`tour-map.js`；短句字幕：`scripts/production/tour_subtitles.py`。
- 回归：`test_tour_pages.py`、`test_tour_subtitles.py`、`test_tour_route_panel.mjs`；真实生成页检查：`scripts/test_tour_pages_browser.mjs`。

- `scripts/production/tour_stage_gate.py`：确切视频的用户确认、讲解准备和合成；`assets/h5/tour/narration-job-template.json` 为任务骨架，确认记录不自动批准。

- `references/local-version-closeout.md`：本地阶段版本、完整回归入口、能力及案例验收边界。
