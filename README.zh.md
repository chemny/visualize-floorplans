# 家装助手 · Interior Design

[English](README.md) | 中文

## 项目简介

面向房主和装修设计团队，从一张户型图开始，完成家具布局、装修风格选择、可编辑的 2D/3D 工作台和配套装修效果图。

家具布局图、风格参考图都不是必需材料。户型图、家具布局图和三维预览使用同一套方案。

## 效果预览

![家装助手功能示意：户型图、家具布局与室内空间](assets/interior-design-hero-simple-zh.png)

| 二维图纸与家具编辑 | 三维观察与显示效果 |
| --- | --- |
| [![二维工作台操作](assets/demos/jujian-workbench/2d-operations.jpg)](https://chemny.github.io/assets/floorplan/demos/jujian-workbench/2d-operations.mp4) | [![三维工作台操作](assets/demos/jujian-workbench/3d-operations.jpg)](https://chemny.github.io/assets/floorplan/demos/jujian-workbench/3d-operations.mp4) |
| 切换图纸，旋转、拖动家具，查看尺寸并撤销操作。 | 鸟瞰、顶面、剖切、房间聚焦与昼夜切换。 |

### 全屋导览

https://github.com/user-attachments/assets/51f3b6ef-f170-41ec-b54c-65b9fc957abf

[查看完整案例](https://chemny.github.io/project-interior-design.html)

## 核心功能

| 能力 | 它能帮你做什么 |
| --- | --- |
| 从一张户型图开始 | 设计前核对房间、尺寸、墙体、门窗和入口关系。 |
| 家具布局建议 | 按居住需求安排靠墙家具、通道、开门净空和窗帘留位。 |
| 看图选风格 | 先在一张图中比较九种室内装修风格，再做选择。 |
| 可编辑 2D/3D 工作台 | 修改家具、门、可拆改墙体和材质，鸟瞰或漫游查看同一方案。 |
| 精细编辑 | 复制物件、右键插入组件、对齐吸附、测量和撤销重做。 |
| 保存与确认 | 保存、导出和继续编辑方案，记录阶段确认。 |
| 配套装修效果图 | 根据确认的布局、风格制作房间及全屋效果，逐图检查差异。 |
| 阶段性清理 | 经确认后清理失效素材，保留恢复途径并保护当前成果。 |
| 本地交付 | 汇总工作台、图纸、方案数据和选定效果图，附文件索引与完整性检查。 |
| 按需制作导览 | 规划路线、预演镜头，选择标准或高质量渲染；视频确认后制作讲解与字幕。 |

用于概念设计，不替代现场测量、结构鉴定或施工图设计。

## 安装

将以下内容发给你的 Agent：

```text
帮我安装这个 Skill：https://github.com/chemny/visualize-floorplans
先检查基础环境；缺少依赖时说明安装方案，经我确认后再安装，并验证能否正常使用。
```

基础功能需要 Python 3.11 或更新版本及现代浏览器。效果图和导览所需工具按需配置；客户端与系统支持情况见[运行环境说明](references/platform-runtime.md)。

## 快速开始

基本流程：**核对户型与需求 → 安排家具布局 → 选择风格与输出成果**。

上传一张户型图，然后说：

```text
帮我设计这个家。我没有家具布局图，也没有风格参考。
先核对户型，建议实用的家具布局，并给我看装修风格选项；确认后制作可编辑的 2D/3D 工作台和装修效果图。
```

## 使用示例

### 调整家具布局

```text
家里住三个人，书房兼客卧。请保证主要过道通畅，在工作台里展示建议的家具布局。
```

### 看图选装修风格

```text
用已确认的客餐厅布局，在一张对比图上展示九种风格，保持同一个人眼高度视角。推荐一种，并说明原因。
```

### 继续修改方案

```text
我已经在本地工作台保存了修改。请读取保存后的方案，按确认布局继续。
```

跨设备继续编辑时，请带上保存后的工作台或方案文件。

### 按需制作导览

```text
根据这套确认方案，制作连续的房主导览。各主要房间要看清楚，转弯平缓。
```

先确认路线和镜头并预演，再制作视频；视频确认后制作讲解。导览支持字幕、路线图与章节定位。

[使用说明](references/guided-user-workflow.md) · [参考案例](assets/reference-cases/)

## 许可

原创代码与文档使用 [MIT](LICENSE)。上游及依赖许可见[第三方说明](THIRD_PARTY_NOTICES.md)；案例素材保留各自权利。

由 [chemny](https://github.com/chemny) 维护 · [问题反馈](https://github.com/chemny/visualize-floorplans/issues)
