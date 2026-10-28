# 成组修改、使用状态及最终图形：layout-review/1扩展

沿用 `furniture-layout-review.md` 的房间、家具组、修改意图与版本证据；本契约只补可执行记录，不另定空间尺寸，也不要求满墙柜、等深柜或某种门型。实现为 `scripts/layout_use_review.py`，由原 `layout_review.py` 及其既有 `h5.py build` 入口调用。

## 整组改造意图

用户要求“通体、包入、整墙、成套”时，将台面/设备/上下收纳及相邻使用关系作为一个功能组。先在原用户意图证据中区分保留、增加、整合与可调整部分，再映射到已有组，不只改单件名称或外框。空间利用率按可取用、通行、清洁和检修评价；允许有依据的深度变化，但不能违背用户明确要求的统一深度。

在原record添加 `assemblyIntents`：每项有 `groupId`、`functions:[{name,memberIds}]`、`requirements`。一个对象可承担多个功能，多个部件也可属于同组；此字段不规定固定对象数量。requirements复用原有pose/count/gap/aligned/uniform_depth等计算关系，不另建尺寸规则。保留的设备位置、台面范围、分段深度和组合数量应有可检查目标；仅写“美观、通体”不能证明完成。

## 使用状态组合

沿用原 `groups.useStates` 的观察和证据，另以 `operationMatrix` 把必要状态落到几何检查。独立区分本体、门/柜/抽屉及把手的运动、人的站位及接近路线。本体不撞不能替代后两项。

- `actors` 为角色→命名状态列表，如roomDoor:[open,closed]、cabinet:[stowed,extended]、person:[using]；不把某案例状态强制为通用默认。
- `motionIncludesHandles:true` 表示声明的运动包络含把手；没有产品或包络依据时保持未核验，不填true冒充实测。
- `scenarios` 每项包含id、完整states、expected（usable或blocked）、snapshot。所有列出的角色状态至少被实际检查一次；无需穷举无关组合，但必须包含日常、取物及相互干扰组合。
- snapshot为hash绑定JSON，含当前stateSha256、相同states、checks。checks分别有非空body、motion、use列表，由代码计算结果，不接受只填pass。支持rect_clear、segment_clear、path_clear；最后一种验证声明的连续路径及障碍，不能仅画箭头。
- blocked须有reason及 `disclosure:{text,artifact}`，原样条件文字必须出现在hash绑定的交付说明/页面中。至少有一个usable组合。已知“关门才能取物”可以是带条件方案，但不能写成所有状态可用，也不等于用户已接受；与用户硬性要求冲突仍应返工。

数值输入结构：rect_clear用a/b两个[x0,y0,x1,y1]矩形；segment_clear用a/b端点、rect障碍和padMm；path_clear用points、obstacles矩形列表和radiusMm。步长、人体尺寸、把手包络及产品机制由案例声明，模块不提供住宅通用阈值。截图外形不代表动作实现；未实现的机制只能按明确包络验证并披露边界。

## 最终二维、三维和截图

新模型或修改后的视图必须检查最后生效的绘图入口及实际输出，不能只检查原始参数或早期函数。特别检查凹口/分段深度、台盆等内部位置、门扇数量及开闭状态；相同外包框不足以证明内部一致。

`finalRepresentations` 包含plan/mesh/screenshot三份receipt引用及各自observation（复用原observed_clear、文字及hash证据）。receipt为JSON：

- stateSha256对应本方案，artifact指向实际SVG、网格测量文件或PNG及其sha256；相对路径从receipt所在目录解析。
- plan/mesh的measurements为同名测量映射；comparisons列出measurement和非负tolerance。依据修改意图选择必要测量，轮廓与内部设备位置不能互相替代。必须从最终SVG及实际场景网格提取，不用两份原配置互相比对。
- screenshot的renderedStates须与expectedScreenshotStates一致。animationSamples含实际姿态actual、目标target及tolerance；采样来自渲染对象，等待收敛后才截图。设置状态后立即截图、仅等待固定时长、或把目标值直接写成实际值均不能作为到位证据。

代码校验hash、状态、测量及数值收敛；不能自动证明截图内容或测量来源诚实，所以仍保留实际观察及生成脚本。二维符号覆盖或动画未到位时，修正最后执行入口/捕获时机，重新导出受影响视图，不靠改文案通过。

## 覆盖与兼容

新整组改造在record声明 `requiredChecks:["assemblyIntentCheck","operationMatrixCheck","finalRepresentationCheck"]`，缺项阻断。其他任务按实际范围声明必需项；普通移动不必无条件增加全套记录。旧记录兼容，但各扩展缺失会返回not_provided，不能视作已经检查。条件组合返回pass_with_conditions；用户批准及现场安装始终独立。

测试见 `scripts/test_layout_use_review.py`：整组只改名/范围不符、只有柜体不撞却无法站人、遗漏状态或把手、条件未披露、旧二维全深图例覆盖浅柜、台盆偏移、截图状态错误、动画中途、陈旧证据等合成反例。案例尺寸、ID和专用柜体渲染不得复制进共享实现。
