# 装修效果视频制作流程

本文件仅约束显式选择的生成式装修处理分支；标准 H5 / Blender 同源渲染遵循 `tour-render-branches.md`，不强制调用本分支。

执行版本：`homeowner-decorated-tour/1`。页面遵循 `four-stage-presentation/1`。

固定顺序为参观路线 → 镜头预演 → 视频审阅 → 讲解成片；本可选分支的装修处理位于第三步。
第二步是同源实时三维，不要求先编码完整三维MP4。已有确认视频可用于提帧；
没有视频时使用当前renderer按tour帧导出的PNG与对应来源记录。已有三维视频不等于装修效果视频。

## 原生制作边界

1. 冻结当前tour、布局/风格bundle、config、机位图和明确的执行授权；源素材记录路径和内容哈希。
2. 按镜头难度与后端时长能力分段，不改变路线或全片时间。关键帧优先覆盖过门前、门槛、遮挡揭示与主体完整显露，不能仅靠平均抽帧。
3. `tour_decorated.py prepare`输出分段与原片/局部帧号。相邻段可共用边界关键帧：前段把它用于生成尾部条件、仅交付边界前的帧，后段从该帧开始，避免重复播放。
4. Agent调用现有Codex原生图片工具编辑每张同机位原图；CLI只登记产物，不能声称自动调用原生工具。工具不返回版本时不写成已核验某个Image版本。布局依据与风格参考明确区分。
5. Agent实际对照原图后用 `review_image`记录构图/布局/未新增设施/风格一致检查与证据，内部检查不等于用户接受。不得只根据文件存在填通过。失败图先修，不能直接渲染。
6. 先选择困难短段；已明确授权继续并有对应试样证据时可以扩展生成。记录实际授权范围，不把短样、测试或生成指令伪造为成片验收。
7. `render`显式指定远程ComfyUI与已有客户端，读取实时节点能力。默认时间关键帧FL2VA方法；轮廓/深度仅为经过匹配对照的可选策略，不能默认叠加。无自动安装、全局中断、无限重试或改变服务配置。
8. 保存提交意图、固定客户端ID、图和输入身份。超时或中断后先找原任务；未知提交结果停止报告，不盲目重复提交。只重做失败片段，已完成且输入未变的片段复用。
9. `assemble`检查每段的帧率、帧数、尺寸、来源与顺序，再无变速拼接为静音待审视频；模型多出的尾帧裁掉，不改变其余时间。不用淡入淡出掩盖空间错误。
10. 完整播放并核对门窗边界、家具增减/漂移、过门时机、接缝、闪变和节奏。美观、结构、时间、动态观感分别记录。低分辨率、一个种子或一个短段不能证实全片一致。
11. 第三步绑定完整装修视频及待确认记录。用户明确确认这一文件后，原有 `narration-prepare/compose` 验证同一视频哈希，再复用/对齐讲解与固定音量背景音乐。旧三维视频批准和旧配音存在不能批准新画面。

扩展短样时保留已验证的关键帧密度和遮挡事件约束，不能一边扩展全片一边未经对照地放宽时间间隔。
近墙退出、普通过道同样可能被模型补成不存在的电视、地毯或窗帘；提示词限制不能代替实际视频检查。
服务空间使用本段独立的白色饰面提示，不能让全局法式提示添加装饰柜或窗景。
失败段保留失败证据，以新段标识和局部新增关键帧修正，已通过段的来源身份保持稳定；拼接入口拒绝已标记失败的段。

`assets/h5/tour/decorated-presentation-job-template.json` 展示生成式分支四步全部字段；按当前步骤省略尚未产生的 `video`、`decorationResult`、`videoReview` 和 `narration`。
第一、二步可只传 `preview`；第三步绑定 `decorationPlan`、装修 `video` 与 `decorationResult`；第四步才增加确切批准和声音字段。

## 现有入口（也可从 h5.py 的 decoration-plan/check/render/assemble 调用）

```text
python scripts/production/tour_decorated.py prepare --job JOB --out NEWDIR
python scripts/production/tour_decorated.py check --plan NEWDIR/decoration-plan.json
python scripts/production/tour_decorated.py render --plan PLAN --remote EXPLICIT_COMFY_URL --client-module EXISTING_CORE_PY --ffmpeg EXISTING_FFMPEG
python scripts/production/tour_decorated.py assemble --plan PLAN --out NEW_ASSEMBLY --ffmpeg EXISTING_FFMPEG --ffprobe EXISTING_FFPROBE
```

模型名称、步数、分辨率、种子、时长、关键帧数量、家具风格及控制强度留在案例配置。
四秒试样暂选无轮廓的A方法；不是跨户型效果保证。渲染服务失败保留原预演可用，不能把三维底稿改名为装修成片。

续做使用每段独立上传记录与已提交图；远程文件名变化不能当成图片内容变化。恢复旧记录须校验原上传图的真实字节哈希，不直接重新提交。断网只续查原任务，未知提交结果停止并报告。

局部接缝修订允许后段引用前段实际末帧作连续引导，记录实际来源帧与目标帧的偏移；不能把重新生成的近似图当成同一边界。未改片段通过 `frozenSegments` 绑定原计划、原输入身份、原收据和视频字节，保留原生出处，不重新渲染或伪造新输入收据。来源、时间、渲染配置或文件改变时冻结失效；已知视觉失败不会因冻结获准拼接。
