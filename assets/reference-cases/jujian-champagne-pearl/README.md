# 居间 · 香槟珍珠参考案例

打开 `index.html` 查看原始素材、13张效果图、2D/3D工作台与56秒连续导览。保持目录结构即可移动到另一台电脑离线浏览。3D需WebGL。Skill不会自动弹出案例；可让智能体“打开内置参考案例”，或从Skill README点击入口。

## 文件索引

- `inputs/`：用户提供的2张原始参考图。
- `workbench/index.html`：当前beta.4单文件演示，保留已测试文件字节。
- `data/case.json`：当前案例输入，原图采用相对路径，可用 `h5.py build` 重建。
- `data/scheme.json`：与上述案例初始状态一致，可在工作台导入。
- `drawings/`：选定户型、家具布局SVG/PNG和硬装PNG。
- `images/`：13张选定的AI概念效果图，原始字节不变。
- `tour/`：选定56秒H5视频、路线、脚本与相机数据；无需三维运行时即可播放MP4。
- `data/media-source-mesh.json.gz`、`media-source-metadata.json`：既有导览来源网格及元数据，普通浏览无需解压。
- `manifest.json`：文件用途、表示范围、大小及SHA256索引。
- `licenses/`：第三方许可。

## 表示范围

当前beta.4演示增加了客厅、入口主灯，并将书房主灯换为吸顶灯；素面大理石、交互、灯光运行逻辑也已调整。其基础墙体模型与既有导览来源一致，但效果图、导览、图纸和网格没有随本次演示重新生成。AI图还保留既有概念光色与局部门扇表现。不能把旧素材的确认转移给最新演示，或把所有文件描述为同一渲染版本。参考案例展示各类输出的能力与已选效果，不替代新项目的结构、视觉和用户确认。

## 重建

让智能体读取 `data/case.json`，执行：

```text
python scripts/production/h5.py build --case CASE_DIRECTORY/data/case.json --out NEW_WORKBENCH.html
```

将占位符换成实际路径。创建新案例时复制并改名，不改通用模板，不继承本案例确认，不照搬其尺寸、家具或风格。此目录不包含中间版本、核验记录或Blender工程。

## 素材权利

本案例按提供者要求公开，作为Skill的参考展示。素材保留各自原有权利；源码的MIT许可不授予独立素材的商用或再分发许可。
