# 追加给 ChatGPT 的项目计划上下文

请把下面这份 Word 项目计划书也纳入教学上下文。之前我已经给过你 MediaPipe / FaceDetector 修复计划；现在请把它放进完整的 AIFX Phase 1 项目中，接下来一步一步带我完成整个项目，而不是只停在人脸检测模块。

我有两份 Word 文档：

- `plan book/AIFX_Phase1_Project_Plan_Zooey_CN.docx`
- `plan book/AIFX_Phase1_Project_Plan_Zooey.docx`

中文版本是主版本，英文版本是对应版本。以下是中文计划书的内容整理。

## 项目计划书

AI 人脸处理与集成项目 - Phase 1

面向 AIFX Studio 集成的人脸检测、裁剪与核心系统搭建

准备对象：Zooey / AIFX Studio Phase 1 Review

准备日期：2026 年 6 月 29 日

执行周期：4 个工作日立即开始；第 1 天当前剩余约 4 小时

截止日期依据：按邮件中的 2026 年 7 月 6 日作为硬截止；PDF 中写的是 2026 年 7 月 27 日

推荐交付方式：优先完成本地 Docker 可运行原型；如时间允许再补充云端部署

## 1. 项目范围与目标

本阶段目标是为后续 ComfyUI 换脸工作流建立基础能力。Phase 1 不需要真正执行换脸，但必须完成可靠的人脸检测、精准裁剪、元数据保存、对象存储、用户认证、任务历史、文档说明和容器化交付。

必须完成：

- 用户可以注册、登录，并进入受保护的工作区。
- 系统支持上传 `.jpg` 和 `.png` 图片。
- 后端使用 Google AI Edge MediaPipe Vision Tasks FaceDetector 进行人脸检测。
- 系统可以裁剪所有检测到的人脸，并优雅处理无脸图和多人脸图。
- 保存原图像素坐标下的 `x_min`、`y_min`、`width`、`height`。
- 持久化保存原图 URL、裁剪图 URL、bounding box、时间戳和任务状态。
- 提供按用户隔离的任务历史页面。
- 交付 Docker 本地运行方案和简明 README 文档。

执行摘要：Phase 1 需要交付一个功能完整、可容器化运行的原型系统。用户登录后可以上传图片，后端使用 MediaPipe 检测人脸并裁剪每一张脸，同时保存原图、裁剪图、精确像素坐标和任务历史。该计划将 PDF 要求压缩为 4 天执行路径，第一天重点完成项目搭建和核心风险验证。

## 2. PDF 要求对应实现表

| PDF 要求 | 实现计划 | 验收证据 |
|---|---|---|
| 后端人脸检测 | FastAPI 接口调用独立的 MediaPipe 检测服务模块。 | 上传图片后返回检测结果、裁剪图和 bounding boxes。 |
| MediaPipe Vision Tasks | 使用 Python MediaPipe FaceDetector，并在启动时加载模型文件。 | README 说明模型来源和本地启动方式。 |
| 裁剪逻辑 | 将相对坐标转换为原图像素坐标，并使用 Pillow/OpenCV 裁剪。 | JSON 中包含 `x_min`、`y_min`、`width`、`height`、`image_width`、`image_height`。 |
| 数据库与认证 | 使用 Supabase Auth 与 Postgres `task_history` 表。 | 用户登录后只能看到自己的历史任务。 |
| 对象存储 | 使用 Supabase Storage 存储原图和裁剪图，文件名使用 UUID。 | 持久化资源不依赖本地磁盘。 |
| 用户界面 | Streamlit 实现登录保护、上传工作区和历史任务面板。 | 三个视图覆盖 PDF 中的 UI 要求。 |
| 容器化 | 提供 Dockerfile 和 docker-compose。 | 评审者可按 README 在本地运行。 |
| 文档 | 提供 `.env.example`、schema SQL、README 和测试说明。 | 评审者可以初始化并操作原型系统。 |

## 3. 推荐技术架构

推荐技术栈为：FastAPI 后端、Streamlit 前端、MediaPipe Vision Tasks 人脸检测、Supabase Auth/Postgres/Storage 持久化，以及 Docker Compose 本地交付。

| 层级 | 技术选型 | 选择原因 |
|---|---|---|
| 前端 | Streamlit | 最快实现上传、预览、登录保护和历史表格。 |
| 后端 | FastAPI / Python 3.12+ | 轻量 API 路由，便于和人脸处理逻辑分离。 |
| 检测核心 | MediaPipe Vision Tasks FaceDetector | 满足 PDF 要求，并能提供准确的人脸框。 |
| 图像处理 | Pillow 或 OpenCV | 用于根据坐标稳定裁剪人脸图。 |
| 认证与数据库 | Supabase | 托管认证和 Postgres 一体化，减少开发时间。 |
| 对象存储 | Supabase Storage | 与认证/数据库同一平台，支持 UUID 文件名和 URL 访问。 |
| 部署 | 本地 Docker Compose | 在时间紧张下优先满足可部署要求；云端部署作为可选项。 |

注意：当前本机环境中，最新版 `mediapipe 0.10.35` 不再提供 `mp.solutions`；而直接使用新版 Tasks FaceDetector 在 macOS 上会触发底层 Metal/OpenGL 服务错误。因此当前已采用兼容实现：保持最新版 `mediapipe`，下载 MediaPipe 官方 BlazeFace `.tflite` 模型，并用 `opencv-contrib-python` 的 `cv2.dnn.readNetFromTFLite()` 执行推理。请在教学时解释这是当前本机可运行的工程替代方案。

## 4. 核心数据模型

建议由 Supabase Auth 管理用户身份。业务数据库只需要保存与认证用户关联的任务历史。

| 字段 | 类型 | 用途 |
|---|---|---|
| id | uuid primary key | 任务唯一标识。 |
| user_id | uuid | 关联 Supabase 认证用户。 |
| original_image_url | text | 原图对象存储 URL。 |
| cropped_image_urls | jsonb | 多张裁剪人脸图 URL 数组。 |
| bounding_boxes | jsonb | 每张脸的像素坐标和置信度。 |
| status | text | pending / completed / failed。 |
| error_message | text nullable | 失败原因，便于调试和评审。 |
| created_at / updated_at | timestamp | 任务审计时间。 |

Phase 2 坐标准备要求：每一张检测到的人脸都必须保存相对于原始全分辨率图片的坐标，而不是前端预览图坐标。必需字段包括 `face_index`、`x_min`、`y_min`、`width`、`height`、`confidence`、`image_width`、`image_height`。

## 5. API 与前端流程

后端 API：

- `GET /health`：健康检查接口。
- `POST /detect-faces`：接收图片、校验用户、上传原图、检测并裁剪人脸、上传裁剪图、写入任务历史。
- `GET /tasks`：返回当前登录用户的任务历史。
- `GET /tasks/{task_id}`：返回单个任务详情，便于调试和审核。

前端视图：

- Authentication Guard：注册/登录页面，未登录时不能进入工作区。
- Workspace：图片上传、原图预览、裁剪人脸预览、坐标信息展示。
- Task History Dashboard：展示历史任务的状态、时间、URL 和 bounding box 摘要。

## 6. 四天交付排期

| 日期 | 主要目标 | 具体工作 | 完成标准 |
|---|---|---|---|
| Day 1 - 6 月 29 日，剩余 4 小时 | 项目搭建与风险验证 | 仓库结构；依赖文件；前后端骨架；数据库草稿；模型测试。 | 前后端可启动；`/health` 可用；README 骨架完成。 |
| Day 2 - 6 月 30 日 | 检测与裁剪核心 | 检测服务；坐标转换；多脸裁剪；无脸处理；测试图片验证。 | 无脸/单脸/多脸均返回正确结果与像素 metadata。 |
| Day 3 - 7 月 1 日 | 认证、存储与历史记录 | 用户认证；对象存储；任务历史；用户隔离；前端展示。 | 用户可上传图片、获取 URL，并查看历史任务。 |
| Day 4 - 7 月 2 日 | 容器化与交付整理 | Docker；README；schema SQL；最终 QA；边界测试。 | 评审者可本地运行，并核验 PDF Phase 1 要求。 |
| 7 月 3 日-7 月 6 日缓冲 | 提交前加固 | 问题修复；可选云端部署；README 完善；代码清理。 | 满足邮件中的 7 月 6 日截止要求。 |

## 7. 第一天剩余 4 小时执行计划

| 时间段 | 行动 | 产出 |
|---|---|---|
| 0:00-0:30 | 确认仓库结构并创建依赖/环境文件。 | requirements/pyproject、`.env.example`、基础目录。 |
| 0:30-1:15 | 创建 FastAPI 骨架和 `/health` 接口。 | 后端可本地启动。 |
| 1:15-2:00 | 创建 Streamlit 骨架，包含登录/工作区/历史占位。 | 前端可本地启动。 |
| 2:00-3:15 | 对一张本地图片运行 MediaPipe FaceDetector smoke test。 | 确认模型路径和检测返回结构。 |
| 3:15-4:00 | 起草 Supabase schema SQL 和 README 启动步骤。 | Day 2 前数据库/存储方案明确。 |

## 8. 完成流程

1. 初始化环境与仓库结构：创建 `backend`、`frontend`、`core_ai`、`database`、`docs` 等目录。
2. 优先实现独立的人脸检测模块，检测逻辑不依赖数据库或前端。
3. 本地检测通过后，再通过 FastAPI 暴露检测接口。
4. 确认裁剪结果正确后，再接入对象存储和数据库持久化。
5. 连接 Streamlit 前端、后端 API 和 Supabase Auth。
6. 补充历史任务面板和用户数据隔离。
7. 完成 Docker 容器化和精确本地启动文档。
8. 按最终验收清单逐项 QA 后提交。

## 9. 风险登记表

| 风险 | 影响 | 应对策略 |
|---|---|---|
| 邮件和 PDF 截止日期不一致 | 若只按 PDF 日期执行，可能导致实际延期。 | 按 2026 年 7 月 6 日作为硬截止；将 7 月 27 日视为文档不一致。 |
| MediaPipe 依赖或模型加载异常 | 阻塞核心要求。 | Day 1 先做 smoke test，再扩展数据库和 UI。 |
| Supabase Auth 集成耗时超预期 | 影响用户隔离历史记录。 | 优先使用 Supabase SDK；必要时先保留单用户 demo，再恢复认证隔离。 |
| Storage URL 权限配置错误 | 评审环境可能无法查看图片。 | 使用 signed URL 或受控 public bucket，并在 README 说明。 |
| 无脸/多人脸边界情况遗漏 | 影响评估结果。 | Day 2 明确加入 API 处理和手动测试用例。 |
| Docker 配置太晚才发现问题 | 影响交付可运行性。 | Day 4 上午完成 Docker 文件并立即测试。 |

## 10. 最终验收清单

- [ ] 用户可以注册并登录。
- [ ] 只有登录用户可以进入工作区和历史任务。
- [ ] 用户可以上传 `.jpg` / `.png` 图片。
- [ ] 后端通过 MediaPipe 检测人脸。
- [ ] 每张检测到的人脸都被裁剪并可预览。
- [ ] 无脸图片返回友好提示，不崩溃。
- [ ] 多人脸图片生成多个裁剪结果。
- [ ] Bounding boxes 保存为原图像素坐标。
- [ ] 原图和裁剪图以 UUID 风格文件名保存到对象存储。
- [ ] 任务历史保存 URL、bounding boxes、时间戳、状态和 `user_id`。
- [ ] README 中的 Docker/本地启动步骤可用。
- [ ] `.env.example` 和数据库 schema SQL 已包含。

## 11. 最终交付物

| 交付物 | Phase 1 是否必需 | 说明 |
|---|---|---|
| Git repository | 是 | 结构清晰，提交记录可追踪。 |
| FastAPI backend | 是 | API routing 与 MediaPipe 核心逻辑分离。 |
| Streamlit frontend | 是 | 认证、工作区、历史任务。 |
| MediaPipe detection module | 是 | 后续可复用于 Phase 2 集成。 |
| Supabase schema SQL | 是 | 包含 `task_history` 以及 storage/auth 设置说明。 |
| Object storage integration | 是 | 原图和裁剪图持久化。 |
| Docker / docker-compose | 是 | 本地部署路径。 |
| README.md | 是 | 安装、环境变量、数据库初始化和运行命令。 |
| Hosted deployment URL | 可选 | 仅在本地 Docker 原型稳定后再做。 |

推荐执行原则：前期不要把时间花在 UI 美化上。优先保证 MediaPipe 坐标转换和裁剪链路可信，因为 Phase 2 的回贴/重合成流程高度依赖准确 metadata。

## 请你接下来这样带我

请从当前项目状态开始，不要重新假设我是空项目。当前已经完成：

- `core_ai/face_detector.py` 已可运行。
- `core_ai/models/blaze_face_short_range.tflite` 已下载。
- `core_ai/test_ai.py` 的空白图测试可通过。
- `mediapipe` 保持最新版 `0.10.35`。

接下来请按项目计划带我继续：

1. 先检查当前仓库结构和已完成内容。
2. 指导我补齐 `requirements.txt` 和 `.env.example`。
3. 创建 FastAPI 后端骨架和 `/health`。
4. 把当前 `FaceDetector` 接入 `POST /detect-faces`。
5. 做图片裁剪和多人脸/无脸处理。
6. 再进入 Streamlit 前端、Supabase、历史任务、Docker 和 README。

请继续保持“每次只给我一个小步骤，等我回复完成后再继续”的教学方式。
