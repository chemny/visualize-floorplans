# Furniture placement principles

Read with furniture-layout-review.md before proposing or revising any layout.
These are concept-design and review rules, not building regulations. Source
structure and consequential uncertainties remain authoritative.

## Required checks

- Design for everyday convenience from confirmed household needs; do not invent
  age/family roles. Complete each room's functions before decorative additions.
- Bedrooms need sleeping, clothes storage and reachable bedside placement
  (nightstand, shelf or integrated surface). Extra cabinets are not mandatory.
- Preserve accepted walls, access and windows. Never relocate an opening merely
  to rescue poor furniture placement. Proposed alterations need their own review.
- Check doors, drawers, cupboard/appliance operation, pulled-out chairs, bed
  access and continuous everyday routes in use, not footprints alone.
- Study/guest rooms require separate daily and sleeping states. Document actual
  expanded furniture dimensions, simple conversion steps and remaining access.
  A sofa footprint cannot certify its unfolded use; avoid moving heavy furniture.
- Wet equipment depends on evidenced services. Keep unknown services unverified.
- Record dimensions as source/derived/design assumptions. Unclosed dimension
  chains and unknown door swings limit clearance checks and must be visible.

## Preferred placement, with explicit reasons for exceptions

- Select a usable headboard wall before placing a bed. Prefer a solid wall and,
  when feasible, avoid the entrance's first sightline directly onto pillows/head.
  Assess the actual entry view, not merely the door's compass direction.
- Avoid unsupported bed islands and purposeless perimeter gaps. A double bed
  centered along its headboard wall can be appropriate; a single bed may use one
  side against a wall if access and occupant needs permit.
- Compose bed/bedside/storage as a functional group. Preserve window operation,
  natural light, cleaning access and practicable wardrobe use.
- Living: establish sofa/TV relationship, then coffee access and through routes.
  Dining: face chairs toward the table and check pulled-out seating and entry.
  Entry: shoe/drop storage is optional; add it only when household needs and
  available space justify it, without narrowing the landing.
- Kitchen: organize food retrieval, wash, preparation and cooking continuously;
  use wall-based work surfaces before disconnected islands or scattered cabinets.

## Review evidence

For each room record: placement rationale; entrance sightline; required functions;
operating-state access; trade-offs/uncertainties. Check source geometry, operation,
room composition and whole-home relationships separately. A collision pass alone
is not a reasonable-layout judgment or visual acceptance. Numeric clearance
thresholds must have an identified source or be labelled design targets.

## Lessons from the bundled reference case

Reuse relational reasoning: side-wall headboards offset from entries; complete
bed/bedside/wardrobe groups; opposed sofa/TV walls; dining near kitchen with entry
passage; study seating/storage/work surface; continuous perimeter kitchen units.
Do not copy that apartment's coordinates, dimensions, door directions, style or
household requirements. Historical drawings/media and current workbench are not
all the same revision; inspect their source labels before using them as evidence.

## Interior door placement and use

For proposed residential room doors, prefer inward opening into the destination
room. Choose hinge side by the actual receiving wall and furniture, not arbitrary
start/end defaults. Compare both hinge sides: prefer the open leaf near a side
wall/return, leaving the room entry and circulation clear. Inspect closed, swept
and fully open states in 2D and actual 3D. A collision-free leaf floating across
a room is not a good default. Door-back wall clearance must be recorded against
the actual wall face; dimensions alone do not prove adjacency.

This is a design preference, not an absolute code statement. Preserve evidenced
existing swings unless alteration is authorized. Tight bathrooms, special
access needs, entry constraints or service conditions may need sliding/outward
solutions; explain each exception rather than silently applying it. Do not move
a source opening just to make a door touch a wall. A proposed door relocation
must be marked as design alteration, with affected wall/structure uncertainty.

## Whole-home essential equipment inventory

For an ordinary complete-home proposal, include and verify the following unless
the user explicitly omits/reuses one or an equivalent function is documented:

- Living: sofa, TV and appropriate TV support/mount.
- Bedrooms: beds, wardrobes and bedside placement.
- Dining: table and usable seating for the household.
- Kitchen: refrigerator, cooking appliance, extractor hood, sink, preparation
  surface and base storage. Model extraction separately: a hob is not a hood.
- Bathroom: toilet, basin/bathroom vanity and bathing equipment. A labelled
  empty rectangle is not a functioning bathroom assembly.
- Laundry: washing machine and its workable location/services.
- Access: actual doors/openings with reviewed kinds, hinges and destinations.
- Requested study/guest function: desk, seating, storage and sleeping conversion.

Keep a case inventory with required function, actual object IDs, room, state
presence, 2D representation and 3D mesh presence, plus operation/service status.
Distinguish absent data, hidden projection/layer, and missing mesh. Shared
functions need no duplicate equipment. Above-counter items may overlap in top
view: show a keyed schedule or hard-plan overlay rather than hide the omission.
Do not present a complete renovation scheme with unexplained missing essentials.

## Layout synthesis before coordinates

Apply this sequence to each new home before presenting its first layout. Do not
use a collision-free arrangement as a substitute for room composition:

1. Establish required functions and evidenced constraints: room polygons,
   complete wall faces, door sweeps, window/sill operation and fixed services.
2. Identify candidate headboard and storage wall faces. Prefer usable side walls
   for tall wardrobes/bookshelves; avoid facing the entry or crowding its landing
   when a better continuous side wall exists. This is a preference, not a ban on
   a functional wardrobe opposite a door. Reject obstructed or too-short anchors.
3. Compose furniture groups, not independent objects: bed and reachable bedside
   surfaces, wardrobe with operating space, desk and pulled-out seat, sofa and TV.
   Prefer two bedside units for a double bed when usable circulation remains;
   consider smaller/integrated units before sacrificing access.
4. Compare at least two viable arrangements internally using entry sightline,
   door-back space, continuous circulation, storage access and usable free area.
   Select the arrangement that supports everyday use with fewer awkward gaps.
   Do not add extra cabinets simply to fill an empty rectangle.
5. Check occupied states: cupboard/drawer doors, seated chairs, appliance doors,
   cleaning access and guest-bed expansion. Require separate daily and guest
   states for dual-purpose rooms. Resolve observed conflicts before presentation.
6. Export the selected layout from the same canonical workbench; document brief
   room-level rationale and unresolved operational dimensions. Ask the user only
   about consequential trade-offs, not every coordinate repair.

Keep a case-local layout-review.json with room IDs, candidate anchors, chosen
relationships, required-function coverage, rejected alternatives/reasons,
operational checks and evidence basis. Checks must distinguish observed geometry,
assumed clearances and unverified services. These are generation/review duties;
they do not claim the H5 editor contains an automatic layout optimizer.


## Wall contact and mounted equipment

For a normal home layout, place wardrobes, bookshelves, shoe cabinets, TV bases,
base kitchen cabinets and bathroom vanities with their backs against a usable
finished wall face. Prefer a sofa back against a wall when the room supports it.
A floating sofa or freestanding cabinet needs an intentional room composition
and an explained reason. Dining tables, coffee tables, usable seats and intended
islands retain their functional free space; they are not wall-backed by default.

- Identify the supporting wall ID and inward face before computing coordinates.
  Include half the actual wall thickness; room polygon bounds, wall centre lines
  and visual labels are not substitutes for the finished wall face.
- Rotate the furniture so its back faces that wall and its front opens into the
  room. In the canonical model local +Y is front and local -Y is back. Record the
  back-to-wall gap and supporting wall span; check the full back edge, not just
  the centre point. Reject anchors across doors, windows or demolished spans.
- Use zero gap or a small documented modelling tolerance for ordinary wall-backed
  bodies. Account explicitly for skirting, sockets, plumbing or installation
  clearances. Appliance ventilation is separate: never force a refrigerator or
  other ventilated equipment flush against a wall without its requirements.
- For wall-mounted TV proposals, set actual coordinates, inward orientation,
  elevation and installation gap; name it "wall-mounted" only after those
  relationships have been checked. Set `mount: "wall"` so the 2D projection has
  no tabletop stand. Preserve the screen/cabinet/sofa relationship. Mounting
  substrate, bracket capacity and service routing remain installation checks.
- Validate daily and expanded guest layouts after placement. Adjacent furniture
  may occupy explicit finish-only floor patches, but must never cross uncovered
  floor or change the source room-area authority to evade a placement failure.
- After movement, rotation, resizing or wall changes, recheck the relationship.
  Saved anchor metadata alone is not evidence of current adjacency.

Use `scripts/wall_anchor_layout.py` during case generation: `anchor(furniture,
wall, side, gap)` places the body atomically; `audit(...)` rejects stale positions,
wrong back orientation, insufficient wall span and openings/removed intervals.
Sides describe which side of the wall contains the furniture. Distances are mm.
This helper is a generation/review tool; it does not add persistent automatic
wall-following or a complete furniture optimizer to the editor. Run
`scripts/test_wall_anchor_layout.py` when changing its placement semantics.


## Protect continuous routes before placing dining furniture

Establish entrance landing, room-to-room branches and everyday routes before
placing the dining group. Reserve connected clear strips with case-specific
width targets and endpoints. The table footprint alone is insufficient: include
occupied chairs, rearward chair movement, service access and furniture fronts.
A table must not force everyday travel through occupied seating or squeeze the
only room entry. Check walls and door leaves as well as unrelated furniture.

For each proposal, record route geometry, target width, chair movement assumptions,
observed bottlenecks and the chosen remedy. Translate/rotate the entire dining
group first; compare smaller table/cabinet sizes or fewer surplus seats when
necessary while retaining the household's seating needs. Do not move structural
walls or openings merely to rescue a table position. After furniture or wall
edits, repeat the checks. Passing static footprint collisions alone must never
be reported as a circulation pass.

Use `scripts/layout_access_checks.py` to check declared orthogonal route strips
against bodies and `chair_envelope(...)` against occupied states. Route selection,
network continuity, wall/open-door obstacles and endpoint reachability remain
explicit generation/review duties. This tool does not compute a whole-home path
or enforce movement zones in the editor. Check independent daily and guest states.
Numeric targets are case design assumptions unless supported by an identified
standard or accessibility brief; never treat a sample value as a universal rule.

## Prefer two-wall contact for viable corner cabinets

For wardrobes, bookshelves and other wall-backed storage, identify usable right
angle corners before choosing a mid-wall anchor. When the cabinet fits and its
front remains usable, prefer its back against the long wall and one end against
the perpendicular wall. Avoid arbitrary leftover end gaps at an otherwise viable
corner. An intentionally centered composition, window operation, entrance landing,
service clearance or inaccessible cabinet front can justify another placement;
record the actual reason. A door opening, glazing or wall endpoint without a
perpendicular solid face is not a usable two-wall corner.

Check both finished wall faces, cabinet body width/depth, continuous support,
openings, installation tolerances and front access. Move/resize neighbouring
bedside or desk groups if needed; do not create an inaccessible cabinet merely
to close a cosmetic gap. Preserve paired bedside functions when adjusting them.
Cabinet door/drawer operation must be checked separately from standing clearance.
Use fillers/installation gaps deliberately for actual cabinet fitting; modelling
contact does not replace site measurements or manufacturer installation design.

Use `anchor_corner(...)` and `audit_corner(...)` in `scripts/wall_anchor_layout.py`
for orthogonal geometry. Contiguous collinear wall segments may support one
cabinet without changing their structural IDs or fabricating a new case wall.
Record both supporting wall relationships and measure both gaps after any edit.
Run `scripts/test_layout_access_checks.py` when modifying corner or route logic.


## 床型与柜长：先比较可用尺寸，再确定布局

这是生成与复核家具方案的通用流程，不代表工作台已有自动布局求解器。

1. **按使用需要比较床型。** 不因房间名为“次卧”或只有一位使用者就默认单人床；也不自行推断年龄、家庭关系。需求未限定时，比较至少两个合理的标准床型。若较大床型仍保留进出、床边使用、储物操作及其他必要功能，优先推荐更舒适的可行尺寸，并说明取舍。
2. **调整整个家具组合。** 放大床时同步检查床位、床头柜、衣柜和低柜，不能只改床宽。以实际床架外轮廓、床头厚度和突出部件校核；只知道床垫尺寸时明确外尺寸尚待选型，不能把床垫通行间距视为安装完成后的净宽。
3. **由连续可用墙面确定柜长。** 优先使用不挡门窗的侧墙；有可用直角墙时按背面、端面共同贴墙定位。沿完成墙面计算从墙角到门洞或其他障碍的有效长度，扣除门套、门扇扫掠、安装收口及必要使用余量后，再根据收纳需求选择成品模块或定制长度。无理由的大段剩余墙面应重新评估，但不能为填满墙面而牺牲门口和柜前使用空间。
4. **区分三种距离。** 柜体端部至门洞的沿墙余量、柜前站立/开启空间、主要通道净宽必须分开记录。沿墙余量大不等于通道畅通，柜前站立无碰撞也不等于柜门或抽屉能完整开启。具体数值是案例的设计目标及模型结果，不能把某案例的数值推广为所有户型的最低规范。
5. **检查日常与转换状态。** 按真实尺寸检查墙体和家具交叠、门扇开启、连续进出路线、餐椅拉出，以及客卧展开等转换状态。为柜门、抽屉采用明确选型的开启包络；缺少选型时列为待复核，不能宣称已完整验证。通常在方案内完成常规位置和尺寸比较，再集中呈现建议及重要取舍。
6. **保留可追溯证据。** 案例记录候选床型、选用理由、柜体可用墙段和端点、选用柜长、实际模型余量、操作包络假设及未核验项。空间确实不足时明确较小床型或非贴角柜体的理由。具体坐标、尺寸和家庭偏好留在案例数据中。


## 床头贴墙与家具使用间距

- 双人床默认以完整床头背面贴合实际完成实墙定位，不能只确认床在房间内而遗漏床头靠墙。用墙面定位、朝向和床头背面间距共同复核；避免窗洞、门洞与门扇扫掠。模型可留极小防穿模量，不能将其扩成无理由空隙。用户明确要求独立床头、或设备/安装条件要求留距时说明例外并确认；不能擅自悬空放床。
- 双人床两侧空间允许时配两只可用床头柜；空间不足时调整床位或柜体尺寸，再说明单侧配置原因。不得仅按物件清单数量完成布置。
- 桌椅应作为使用组合检查椅子面对桌子的位置、坐姿位置、拉出空间和收起状态；沙发茶几应检查座前到桌边的使用距离及相邻通道，避免靠物件中心间距判断。选定距离须保存在案例，不能把本案数字当成所有户型的固定标准。
- 餐桌旋转或靠墙时，连同餐椅方向及数量重排。贴墙的一端不设不可坐的座位，保证家庭常用席位及餐椅拉出后进出路线。外开入户门需单独检查室外门扇扫掠；缺少室外几何时明确尚未核验。


## 窗帘预留与可选玄关收纳

- 在靠窗家具定位前，先标出窗帘轨道/盒、帘布活动深度和两端收拢区域。窗帘预留同样适用于需设帘的阳台推拉门；检查把手、门窗开启和通行。根据单层/双层、褶量和安装方式确定案例包络，不将案例的预留深度作为通用安装尺寸。窗边床头柜、床、书桌及柜体不能侵占该包络；在保留必要使用空间的前提下移动整组家具或缩小配套柜体。
- 玄关柜、鞋柜不是每套方案的强制项目。依据换鞋和随手收纳需求、现有收纳替代位置、门扇及通道空间决定是否设置；没有明确需求时可省略。不能为凑齐家具清单在入户口强行放柜。用户明确不要时，直接移除并复核通道。
