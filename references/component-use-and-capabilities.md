# 门型与家具组件：选择及能力入口

本表回答“何时用、能否省略、和谁一起检查、实际支持到哪里”。完整注册项见 `assets/component-capabilities.json`。注册兼容、目录可见、三维外形、可操作机制、使用空间验收是五件独立的事；清单不构成逐组件视觉验收。

## 使用顺序

先读取家庭场景与必要功能，再选家具族和具体组件，组合布置，最后验日常、开启及转换状态。空间利用率指可达、可取用且保留通行的有效空间，不是摆满物件或最大化柜体面积。便捷性须结合完整动作链和绕行评价。已有完整原则见 `furniture-placement-principles.md`，完整验收见 `furniture-layout-review.md`，此处不另建一套尺寸门槛。

每个组件沿清单中的 family/use/checks 检查；所有选配项允许省略，但不得因此丢失用户要求的功能。先比较组合，再改配套小件；不能把用户要求的“一个完整大衣柜”实现成两段不同深度柜体。来源图与用户修改意图分别记录。

## 能力边界

|层次|实际支持与边界|
|---|---|
|目录与外形|注册项不是默认全部展示；家具以工作台 `homeStudio.getCatalog()`、建筑门窗以 `homeStudio.getArchitecturalCatalog()` 为实际目录，保留隐藏与别名。尺寸默认值是产品假设，不是标准。|
|尺寸与布置|`furniture-size.js`、`dimensions-v9.js` 校验尺寸/标高；`wall_anchor_layout.py` 检查墙角及背面；不等于全屋自动优化。旧模型需另验尺寸与实际网格。|
|家具组合|`layout_review.py` 检查数量、对齐、间距、统一深度、操作区及修改意图，并可核对整组功能、门柜与人的状态组合和最终表示回执（见 `layout-use-and-representation-contract.md`）；定性观察需要真实证据，不是自动审美识别。|
|操作空间|`layout_access_checks.py` 检查声明的通道条带/餐椅包络；冰箱、柜门、抽屉、沙发床应使用选型包络。详细外形不代表动作已实现。|
|设备与灯光|已有灯具绑定和设备外形；水电、通风、承重、照度与产品安装校核须单列，不能从画面推定合格。|
|门与隔断|读 `door-selection.md`。显式单扇平开淋浴门为共享能力；淋浴滑动隔断仍无通用机制，不得冒充支持。|

## 现有执行入口

`production/door_checks.py`：源图身份、门扇数量及逐扇扫掠；`production/plan_route.py`：真实门扇/滑动面板障碍；`layout_review.py`：功能、组合、使用状态、版本绑定证据。`production/h5.py build` 对已附带的 layoutReview/doorSourceReview 执行复核；旧数据缺少记录仍可能构建，必须列为未提供，不能声称自动全覆盖。

已接入建筑构件入口及按门型区分的编辑；单扇侧滑/推拉等与实心、透明、磨砂饰面分开。没有自动产品选型或全屋最优求解。布局构建自动生成 `.doors.json` 名义动作诊断；真实通道须另声明路径，失败不自动改变已确认开法。修改能力表后运行 `python3 scripts/check_component_capabilities.py`。

设施到达、开启、使用和退出的声明检查见 `facility-use-checks.md`；构建输出 `.facilities.json`，缺少声明为not_provided，不能从通过门口推定所有设施可用。

## 可校验的组件行为索引

`assets/component-capabilities.json` 使用 schemaVersion 2。每个注册项都明确保存
`runtimeType` 与 `behaviorProfile`：别名必须和运行时的映射一致，并继承目标的行为，
例如 `basin → vanity`、`sink → ksink`。建筑门窗机制另列在
`architecturalMechanismProfiles`，不能用独立家具门的外形代替真实墙洞。
注册项的 `operation` 保留产品选型与使用验收的保守边界；实际已实现的交互机制
以共享行为中的 `operation` 为准，两者都不能代替当前案例的使用检查。

共享 `behaviorProfiles` 分别记录：

- `resize`：外围如何变化、哪些子部件固定、初始化时机、最小包络和高度/安装面例外。
- `operation`：实际实现、需要显式提供的配置、尚未实现的动作和产品/使用检查边界。
- `representation`：平面与三维的共同方案来源，以及“索引不授予验收”的边界。
- `evidence`：源码、数值/契约测试及实际浏览器检查的入口。文件存在不代表本次已经执行；
  执行情况仍由绑定具体页面指纹的报告记录。

| 类型 | 已实现的尺寸/操作行为 | 不能据此推定 |
|---|---|---|
| 淋浴 | 显式平开门的宽度独立保存；外围扩大时锁边侧补固定玻璃；开关、铰链和把手几何共享 | 没有配置门机制的旧外形可开启；滑动或折叠门已支持 |
| 洗手台及 basin 别名 | 固定盆宽深、盆距及背边偏移；柜体/台面扩大，盆、孔、下水、龙头按局部坐标联动 | 厨房水槽也采用相同固定盆体规则；柜门自动可动 |
| 浴缸 | 初始化一次固定缸体；外围扩展平台；缸体左中右定位 | 拉伸后自动换成新的真实浴缸型号或已通过进出检查 |
| 柜体 | 长、深、本体高和离地独立；顶到完成顶面的派生高度保留 | 尺寸正确就等于柜门、抽屉、操作者和通道可同时使用 |
| 厨房独立水槽 | 自己定位、旋转及改尺寸，适用的同高台面开孔跟随 | 自动继承洗手台的固定盆布局；水槽、备餐、灶动线已合格 |
| 冰箱、洗烘等设备 | 已保存的本体外包络和模型细节 | 门缝/把手外形代表真实开合动画、散热或检修距离合格 |
| 灯具 | 灯具外形显隐与照明贡献分别管理；顶部安装灯具和顶面联动 | 顶面隐藏会关闭照明；所有安装面的灯都要一起隐藏；照度已达标 |
| 踢脚线等收口 | 手动部件与带 assemblyOwner 的派生部件分开；派生部件从所属对象重建 | 所有收口可以脱离所属房间/家具随意独立拉伸 |
| 建筑门窗 | 平开、沿墙单扇侧滑、多扇推拉、对开、隐藏外观、开放口、窗洞分别声明 | 磨砂/玻璃材质新增门机制；普通窗洞有真实可动窗扇；折叠及入墙门已支持 |

单个组件可按需查询，不必加载整张表：

```bash
python3 scripts/check_component_capabilities.py --component shower
python3 scripts/check_component_capabilities.py --component basin
```

维护时执行：

```bash
python3 scripts/check_component_capabilities.py
python3 -m unittest discover -s scripts -p test_component_capabilities.py
```

检查器拒绝注册项遗漏、未知/缺失行为、固定子部件契约缺失、别名继承错配、
证据路径失效和虚报可动机制。类型级数值测试与跨户型浏览器回归仍需分别运行；
不能从组件索引通过推定当前案例布局、实际产品、施工或用户视觉验收通过。

## 家具风格与服务空间

`furniture-style-linkage.md` 列出可换家具体及九种造型族。样式、尺寸、颜色固定和真实操作能力分别记录；外形变化不代表柜门等动作已经实现。共享模块 `furniture-style.js` 与 `room-style-policy.js` 配合 `test_furniture_styles.mjs`、`test_furniture_style_browser.mjs` 检查真实几何和生成页面。

书桌避门使用案例显式 `deskPlacementPolicy.minimumOpeningDistanceMm`，构建输出 `.desks.json`；`production/test_desk_placement.py` 覆盖近门反例、相邻房门、旋转家具和缺少规则。它只检查桌体到本房入口的保守平面距离，坐下、拉椅、柜门和路径仍须 `layout_use_review` 等另验。儿童房是否设书桌属于家庭需求，不能从某个案例推广成默认删除。
