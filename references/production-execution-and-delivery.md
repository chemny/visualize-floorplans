# 渲染执行与交付 SOP

能力契约：`homeowner-production-sop/1`。这是本地共享执行能力，不是已发布版本，
不生成 ZIP、本地分发包或自动推送。具体主机、GPU型号、路径、灯光、采样、
帧率、时长、配音素材、失败样片结论都留在案例配置。

## 固定链路

参观路线 → 镜头预演 → 视频审阅 → 讲解成片。H5 默认，Blender 显式选择。
可选视频放大位于第三步审阅内，不增加主流程页签，也不是必经步骤。
换了视频字节后，旧讲解批准失效；同路线、同帧序和同时间轴可以复用已对齐音轨，
仍须核对文稿事实和目标镜头。纯声音合成复制视频编码帧，保留短句字幕与原音轨引用。

## 远程 Blender

已有 SSH、远程 Python、Blender、FFmpeg/FFprobe 是前置条件；不安装依赖、不改
服务、不停止其他任务。端点只在案例中指定，优先已有 SSH alias。既有静态/短样/
整片授权仍由 `blender_draft.validate` 核对；远程操作另绑定确切任务和端点的用户证据。

任务模板见 `assets/h5/tour/remote-production-job-template.json` 及
`remote-production-authorization-template.json`。授权中的 job/kind/endpoint 必须与任务
完全相同；模板 pending 不允许启动。Blender任务另绑定routeReview、routeScene、routeGeometry；这三个引用也须进入捕获授权，远程重定位后重新验证。执行配置示例为
`blender-execution-optix-template.json`，仅供明确选择 NVIDIA/Windows 的案例采用。
执行前使用h5.py doctor --for blender检查显式Blender、FFmpeg路径；接口支持Blender5.2系列，其他主要版本须先验证。可选择 CPU、Metal、OptiX、CUDA；显式 GPU 不得悄悄退回 CPU。Windows 无显示会话
可在已验证的主机设置 graphicsBackend=vulkan；它不是所有平台统一默认。
远程要求贴图已打包到独立场景副本，源场景不覆盖；未打包图片会拒绝渲染，避免缺纹理。

```sh
python scripts/production/h5.py remote-production --action prepare --job CASE_REMOTE_JOB --out NEW_TASK
python scripts/production/h5.py remote-production --action start --out NEW_TASK
python scripts/production/h5.py remote-production --action status --out NEW_TASK
python scripts/production/h5.py remote-production --action collect --out NEW_TASK
```

prepare 只创建普通执行暂存目录和哈希清单，不连接远端、不创建分发包；start
上传冻结输入与共享脚本快照，再启动脱离 SSH 会话的单次任务，不创建服务/计划任务。
状态分为 preflight/rendering/verifying_frames/encoding/verifying_outputs/ready_for_review/failed。
逐帧进度、实际后端、采样、降噪和计时独立记录。预计耗时只能用当前主机和代表位置
实测估算，注明首次加载、渲染、编码和传输口径，不把历史耗时当承诺。

丢连接后先 status；提交结果未知时禁止盲目重提。仅 failed 且无同任务进程时可
`--action resume`。任务、源码或输入改变必须新建任务。校验通过的帧保留，编码失败
不重渲染；编码临时文件与正式输出分开。Python subprocess 读取真实 returncode，
不把 PowerShell 空退出码当成功或自动改为0。远程Python与子进程固定UTF-8，避免中文报告被Windows默认编码破坏。无法判定时保持失败/未知并核对证据。

渲染和编码均在远端完成。核对全帧哈希、连续源帧、尺寸/帧率/时长后，只回传视频、
报告和少量代表帧；原始帧留远端。收集结果依然 pending，不授予讲解或用户验收。

## 采样、降噪与运动问题分开诊断

质量模板为 `blender-quality-template.json`；实际采样数由案例和短样比较选择，不统一
规定128次。固定/自适应采样、降噪器、辅助通道、随机种子、运动模糊分别记录。
当前精确逐帧姿态捕获明确关闭 motionBlur；缺少真实快门期间相机运动时，不能
借开关声称实现真实运动模糊。需要它时另用经过验证的动画采样方法。

按顺序判断：单帧原始噪点 → 降噪前后是否跳变 → 细线/反射/焦散/几何问题 →
24帧运动步进 → 浏览器解码、显示刷新与网络缓冲。加采样、提分辨率或补帧不能混为一项修复。
比较时冻结家具、材质、照明与路线，仅改变声明变量；最终档位不得暗中低于已确认短样。

```sh
python scripts/production/h5.py video-quality --job QUALITY_JOB --out NEW_QUALITY_REPORT
```

光流诊断需要环境已具备OpenCV；未安装时应明确报告依赖缺口，不自动安装或把该项标为通过。报告分别记录全屏跳变、案例屏幕区域的局部残差和重复图像。光流一致性用于排除
部分遮挡；屏幕区域并非世界坐标表面跟踪，移动高光、镜面、出画仍可能误报。
无全屏报警不能写成无局部闪烁，重复图像也可能是正常停留。真实连续播放与
`media-visual-review-template.json` 分开保留，不能由数值结果自动填写。

## 可选放大短样

`upscale-comparison-job-template.json`：源视频哈希、确切源帧、目标尺寸、方法及
禁止扩散/补帧都需授权。authorization 使用 scope=video_upscale_comparison、
status=approved、approvalSource=explicit_user_confirmation、非空 evidence，settings
精确复制任务中除 schema/authorization 外的字段。首次只做最多5秒，且不得是完整视频。

```sh
python scripts/production/h5.py video-upscale --job UPSCALE_JOB --out NEW_COMPARISON --ffmpeg EXISTING_FFMPEG --ffprobe EXISTING_FFPROBE --comfy EXPLICIT_EXISTING_URL
python scripts/production/h5.py video-upscale-pages --result COMPARISON_RESULT --out NEW_PAGE
```

普通 Lanczos 只改变尺寸，不宣称恢复真实细节。H3-only 为视频VAE编码 → 神经潜空间
放大 → 解码，固定节点白名单，无扩散采样或相机重规划；即便如此仍可能改变细线和纹理。
对齐采用边缘复制补边和放大后去边，不拉伸或裁掉原构图；帧数和帧率必须保留。H3因果视频VAE按照已验证的17k+5帧边界复制末帧作为上下文，解码后移除；这不是补帧，最终帧数不变。
使用已安装节点和模型，不自动下载。断网按原任务ID续查，未知提交禁止重复生成。
比较清晰度、家具边缘、色彩和局部稳定性；没有明显收益或有新瑕疵就保留原片。
当前入口仅是实验短样，不授权处理整片，也不把某次失败写成模型永久不可用。
远程放大使用同一 remote-production，kind=upscale；回传后用 collected/upscale-result.json
生成共享对照页。短样默认不循环、逐版单路播放，避免接头与多路解码影响判断。

## 最终交付检查

```sh
python scripts/production/h5.py delivery-check --job DELIVERY_JOB --out NEW_REPORT --ffmpeg EXISTING_FFMPEG --ffprobe EXISTING_FFPROBE
```

核对确切媒体、完整帧序/时间轴、合成前后视频编码帧、音轨可解码且无削波、
声音与画面时长、音乐固定增益、同版本页面、实际播放及独立视觉记录。
网页字幕样式与 MP4软字幕/SRT不同，不能宣称黑描边已烧录进下载文件。
配音原始参考不得复制到公开目录。新页面验证后才更新当前入口，保留旧版本可回退。
缺少完整播放、独立视觉记录或同版本页面记录时报告 needs_engineering_review，不自动用户批准或发布。

完整播放使用已有 Chrome 和 Playwright，不安装依赖：

```sh
node scripts/production/tour_delivery_browser.mjs --url FINAL_MP4_URL --video EXACT_FINAL_MP4 --out NEW_PLAYBACK_REPORT --browser EXISTING_CHROME --playwright-module EXISTING_PLAYWRIGHT --page-url NARRATED_PAGE_URL --page-video EXACT_SILENT_SOURCE --composition-job EXACT_COMPOSITION_JOB
```

播放器会正常速度完整播放下载版，并核对页面媒体与音轨哈希、四步导航、地图/列表、
字幕、音乐/配音开关、静音和移动宽度。托管视频须支持HTTP Range，避免拖动时回到开头；
工具记录掉帧、缓冲停顿，缺失或失败不能当作已验收。此检查不替代独立的视觉/听觉审阅。
合成原始参考音频不得进入页面目录；页面仅使用已批准的成品音轨。

## 规则—实现—回归

| 规则 | 共享实现 | 检查 |
|---|---|---|
| 明确设备与质量，不继承旧模糊 | blender_execution.py、blender_render_quality.py、capture_blender_draft.py | test_production_closeout.py、现有 Blender API集成检查 |
| 授权、冻结传输、后台任务、恢复与远端编码 | remote_production.py、remote_production_worker.py、blender_draft.py | 合成任务的重定位/篡改/失败阶段/帧校验反例，独立远端短任务 |
| 全屏与局部诊断、独立视觉记录 | tour_media_quality.py、blender_draft_review.py | 小区域闪变不能被全局中位数掩盖；截图不得冒充连续播放 |
| 放大短样和纯放大节点 | video_upscale.py、共享对照模板 | 真实小视频尺寸/帧数、错误比例、修改源帧、禁止采样、未知提交结果 |
| 最终图片/音频/页面/审阅绑定 | tour_delivery.py、tour_stage_gate.py | test_production_browser.py 的真实小素材/新页面集成；原编码帧保留，缺少、过期或被改页面不得放行 |

本机自动回归：`python -m unittest discover -s scripts/production -p "test_*.py"`。
已有浏览器/媒体工具时另运行：

```sh
python scripts/production/test_production_browser.py FRESH_TEST_OUTPUT EXISTING_NODE EXISTING_CHROME EXISTING_PLAYWRIGHT EXISTING_FFMPEG EXISTING_FFPROBE
```

该集成测试创建独立合成视频和新四步页面，执行播放/音轨/字幕交互、改页拒绝及过期记录反例；
不读取当前房屋、不更新交付入口。远程执行与H3实际测试需另显式绑定现有主机/模型，
不会在普通单元测试中偷偷启动远程任务。

测试夹具中的 synthetic approval 仅检验门控，不能当作真实房屋或真实用户确认。
