# 设施完整使用检查

共享入口 `production/facility_use_review.py`，由 `h5.py build` 调用并输出 `.facilities.json`。没有声明为 not_provided，不推定设施可用。声明 required=true 时，缺少范围内设施、动作失败、路径失败均阻止构建。沿用 layout-use-and-representation-contract.md 的“状态、人体、运动、最终表示分别取证”原则，不规定住宅通用人体宽度或具体家具参数。

`facilityUsePolicy:{required,scope:[设施ID],facilities:[...]}`。每项必填 id/from/operator/usePoint/bodyRadiusMm；人体包络、操作点来自案例需求。检查粒度为实际设施，不是“到了房间就算通过”。

- 配置淋浴：家具字段 `showerDoor:{type:'hinged',hinge:'left'|'right',angle:5..100,open:0..1}`。明确为单扇向外平开；未配置保持旧外形，不自动发明开法。front为家具局部+Y，转向沿家具rot。玻璃门与把手、三面围挡、净入口、开关门过程在共享JS/Python几何中表达。
- 淋浴流程：关门状态到外部操作点 → 操作人避开完整门扇/把手扫掠 → 开门后进到内部站位 → 关门后内部站位可用 → 开门退出 → 外部关门并离开。操作点同时能用于关闭动作；没有手臂逆运动学/手力、具体产品选型或专业安装认证。
- 柜体/洗手台：`motion:{type:'front_extension',extensionMm,handleMm,edgeInsetMm}` 显式保守前向操作包络，检查旋转矩形相交、操作人避让、到达、取用后收回、使用及退出。该矩形包络不是已实现的产品抽屉/柜门动画。必须记录依据，不由柜体外框推导所有真实五金动作。
- 静态设施：`motion:{type:'static_use'}` 检查声明使用站位与往返路径；坐姿、轮椅、手部触及需独立声明，不能从平面人体圆推定。
- 必须先关房门才能使用时，显式 `closeRoomDoor:洞口ID,roomDoorOperator:[x,y]`，同时支持平开门和显式单扇侧滑门的关闭状态。额外验证进入站位、关门扫掠不碰人、门关闭后的设施流程及重新开门离开。不能静默把房间门从障碍中删掉。

路径复用 Planner，按实际墙、家具、房门扇/把手、侧滑面板/拉手、淋浴围挡/门扇/把手检查；简化后以5mm采样复查，防止网格/简化擦边误报通过。不是建筑规范认证或全局最优求解。空间狭窄、只能关门取用等条件必须在交付说明披露；不能缩小人体或删掉把手来通过。

优先保留家具与建筑布局。发生冲突后，比较铰链、开启角、侧滑停车墙及真实净开口；确需调整家具时再改变位置或尺寸，并同步平面和三维。已确认案例参数不是共享默认，禁止把某案例坐标、角度、人体尺寸固化为通用规则。

回归：`test_shower_doors.mjs`（JS/Python几何及围挡一致）、`production/test_facility_use_review.py`（正例/缺机制/缺范围/操作人碰撞/运动冲突/净口不足/无效包络/旧数据待核验）、`test_shower_browser.mjs HTTP_URL REPORT`（真实按钮、平面变化、实际玻璃网格姿态、闭合返回与方案不变）。浏览器使用已有INTERIOR_PLAYWRIGHT_MODULE/INTERIOR_BROWSER，不安装依赖。测试数量不代替当前页面和使用空间审阅。
