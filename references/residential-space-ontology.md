# Residential space ontology

Use this controlled vocabulary when interpreting Chinese residential floor
plans. Separate visible geometry from functional identity. Never create a space
to satisfy the vocabulary.

## Naming hierarchy

### Public and circulation spaces

- `entrance`: 入户口
- `foyer`: 玄关
- `living_room`: 客厅
- `dining_room`: 餐厅
- `living_dining`: 客餐厅
- `hallway`: 走廊
- `passage`: 过道

### Private spaces

- `primary_bedroom`: 主卧
- `secondary_bedroom`: 次卧
- `childrens_room`: 儿童房
- `elders_room`: 老人房
- `guest_room`: 客房
- `study`: 书房
- `multipurpose_room`: 多功能房
- `walk_in_closet`: 衣帽间

### Service and wet spaces

- `kitchen`: 厨房
- `chinese_kitchen`: 中厨
- `western_kitchen`: 西厨
- `primary_bathroom`: 主卫
- `shared_bathroom`: 公卫
- `guest_bathroom`: 客卫
- `secondary_ensuite`: 次卧套卫
- `laundry`: 洗衣房
- `storage`: 储藏室

### Exterior and projection spaces

- `balcony`: 阳台（生活/景观属性未确认）
- `living_balcony`: 生活阳台
- `view_balcony`: 景观阳台
- `terrace`: 露台
- `bay_window`: 飘窗
- `equipment_platform`: 设备平台
- `courtyard`: 庭院

### Unresolved spaces

- `unassigned_space`: 待确认空间
- `bedroom_candidate`: 卧室候选区
- `wet_area_candidate`: 湿区候选区
- `exterior_candidate`: 外部空间候选区

## Naming rules

1. Prefer an industry name over ordinal labels after the role is confirmed.
   Do not publish `卧室1` or `卫生间2` as a final label.
2. Use `主卧` only when the drawing labels it, the user confirms it, or multiple
   strong clues support it. Until then use `主卧候选` and show confidence.
3. Use `次卧`, `儿童房`, `老人房`, `客房`, or `书房` only when the role is
   explicit or user-confirmed. Otherwise use `卧室候选A/B`.
4. Use `主卫` only when it connects to a confirmed main bedroom. Use `次卧套卫`
   only when it connects to a confirmed secondary bedroom. Use `公卫` when it is
   reached from public circulation. Do not infer bathroom role from position
   alone.
5. Use `厨房` only with an explicit label or a bounded zone supported by strong
   service evidence such as a flue plus plumbing, counters, or recognised kitchen
   symbols. A single drain or service point is insufficient.
6. Use `书房` only with an explicit label, a clear built-in study arrangement,
   or user intent. A small room is not automatically a study.
7. Distinguish `飘窗`, `阳台`, and `露台` by access and walkability. A bay window
   is a projection, not a room and never part of a walking route.
8. If evidence is insufficient, preserve the bounded geometry and label it
   `待确认空间`; never fill exterior blank space or an open setback with an
   invented room.

## Evidence and confidence

For every functional name record:

- `evidence`: explicit label, user correction, fixture, service point, access,
  enclosure, proportion, or adjacency;
- `certainty`: `confirmed` or `uncertain`;
- `proposed_label`: the user-facing industry term;
- `alternative_labels`: only credible alternatives for the same visible zone.

User confirmation outranks heuristic inference. Visible source geometry remains
the authority for whether a zone exists.
