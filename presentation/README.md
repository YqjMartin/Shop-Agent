# Shop Agent 课程汇报 PPT

本目录存放 Shop Agent 项目的课程汇报演示材料，包含两种形式：

| 形式 | 文件 | 用途 |
|------|------|------|
| 网页版 PPT | `index.html` | 课堂展示主用（浏览器全屏打开，键盘翻页） |
| PowerPoint | `Shop-Agent汇报.pptx` | 交付老师存档 / 离线查看 |

两版内容完全一致，共 **16 张幻灯片**，讲解时长约 10–12 分钟。
关键设计图与演示截图均使用报告模板 `人工智能大作业报告模板.docx` 中的**真实图片**。

---

## 一、使用方式

### 1. 网页版（推荐课堂展示）

直接在资源管理器中双击 `index.html`，即可在默认浏览器中打开。

常用快捷键：

| 按键 | 作用 |
|------|------|
| `→` / `Space` | 下一页 |
| `←` | 上一页 |
| `F` | 全屏 |
| `S` | 打开演讲者备注视图（含讲稿） |
| `ESC` / `O` | 幻灯片总览模式 |
| `B` | 暂时黑屏 |

> 注：页面依赖 jsDelivr CDN 加载 reveal.js。如在无网环境下展示，请提前将 `index.html` 中的 CDN 链接替换为本地文件，或预先在有网环境下缓存浏览器。

### 2. PowerPoint 版

直接双击 `Shop-Agent汇报.pptx`，使用 PowerPoint / WPS / Keynote 打开。

若需重新生成 PPTX（例如修改内容后），执行：

```powershell
# 1. 安装构建依赖
pip install python-pptx pillow

# 2. 运行构建脚本（会覆盖已有的 pptx；若 pptx 正被打开会报 PermissionError，请先关闭）
cd presentation
python build_pptx.py
```

构建完成后 `Shop-Agent汇报.pptx` 会被更新（约 1.2 MB，含嵌入图片）。

---

## 二、内容结构（16 页）

| 页 | 章节 | 标题 | 关键图 / 素材 |
|----|------|------|---------------|
| 01 | 封面 | Shop Agent · 电商管理客服系统 | — |
| 02 | 目录 | 汇报目录 | — |
| 03 | 一、背景 | 项目背景与痛点 | — |
| 04 | 一、背景 | 项目定位与目标 | — |
| 05 | 二、技术 | 技术栈总览 | — |
| 06 | 二、技术 | 系统整体架构 | `diagram-architecture.png`（报告图 7） |
| 07 | 二、技术 | 核心技术（一）Tool Calling | `diagram-tool-calling.png`（报告图 2 · UML 时序） |
| 08 | 二、技术 | 核心技术（二）RAG 产品推荐 | `diagram-rag-flow.png`（报告图 4 · 两阶段） |
| 09 | 二、技术 | 核心技术（三）Router Agent 意图路由 | — |
| 10 | 二、技术 | 核心技术（四）Agent Memory 三阶段 | — |
| **11** | 二、技术 | **数据模型设计（ER 图）** | `diagram-er.png`（报告图 5） |
| 12 | 二、技术 | 系统亮点小结 | — |
| 13 | 三、演示 | 功能演示（一）登录 & 商品推荐 | `shot-miniapp-login.png` + `shot-rag-result.png`（小程序真机截图） |
| 14 | 三、演示 | 功能演示（二）开发端 & 场景 | `shot-streamlit.png`（Streamlit 联调截图） |
| 15 | 四、总结 | 项目总结与后续工作 | — |
| 16 | 四、总结 | 致谢 & Q&A | — |

---

## 三、视觉规范（学术清爽）

- 背景：白色 `#FFFFFF`
- 主色：深蓝 `#1F3A68`
- 强调色：蓝绿 `#2E86C1`
- 辅助文字：中灰 `#566573`
- 分割线：浅灰 `#E5E8E8`
- 标题：40 pt / 粗体；副标题：24 pt；正文：20 pt；代码/注解：16 pt
- 字体：`PingFang SC`、`Microsoft YaHei`、系统无衬线 fallback
- 页脚：`Shop Agent · 课程汇报 · 2026` + 页码

---

## 四、目录结构

```
presentation/
├── index.html                        # 网页版 PPT（reveal.js 单文件，16 页）
├── build_pptx.py                     # PPTX 构建脚本（python-pptx + pillow）
├── Shop-Agent汇报.pptx               # PPTX 产物（由脚本生成，约 1.2 MB）
├── README.md                         # 本文件
└── assets/
    ├── diagram-architecture.png      # 系统架构图（报告图 7）
    ├── diagram-tool-calling.png      # Tool Calling UML 时序图（报告图 2）
    ├── diagram-rag-flow.png          # RAG 两阶段流程图（报告图 4）
    ├── diagram-er.png                # 数据库 ER 图（报告图 5）
    ├── shot-miniapp-login.png        # 微信小程序登录页截图（报告图 1）
    ├── shot-rag-result.png           # 小程序 RAG 推荐结果截图（报告图 6）
    ├── shot-streamlit.png            # Streamlit 联调页截图（报告图 0/开发端）
    ├── architecture.svg              # [旧] 手绘架构示意 SVG（已由 PNG 替代，保留备份）
    ├── tool-calling.svg              # [旧] 手绘 Tool Calling 示意 SVG
    ├── rag-flow.svg                  # [旧] 手绘 RAG 示意 SVG
    └── memory-stages.svg             # [旧] 手绘 Memory 三阶段示意 SVG
```

> `*.svg` 为首版的自绘示意图，现已由报告中的真实图片（PNG）全面替代；保留于目录中以便回溯，HTML 与 PPTX 均不再引用。

---

## 五、事实来源

所有技术描述与量化指标来源于以下项目内部文档，未虚构任何数据：

- `README.md`：项目概述、技术栈、API 端点
- `todo.md`：五阶段开发计划与完成情况
- `AGENT_MEMORY_PLAN.md`：Agent Memory 三阶段实现与**预期收益**表
- `to-fix.md`：已识别的待完善项（Memory 阶段 4、JWT 签名、密码哈希升级）
- `requirements.txt`：技术栈依赖列表
- `app/` 源码目录：架构层次与模块职责
- `人工智能大作业报告模板.docx`：真实设计图与运行截图（共 7 张）

> ⚠️ 关于量化指标：PPT 中出现的 Token ↓80%、成本 ↓76% 等数字，均为
> `AGENT_MEMORY_PLAN.md` 中的**预期收益表**，并非实测结果，所有引用处均已明确标注。

---

## 六、修改指引

- **修改内容**：编辑 `index.html` 中对应 `<section>`，再同步修改 `build_pptx.py` 中对应 `slide_XX_*` 函数即可。
- **修改配色**：`index.html` 顶部 `:root` CSS 变量 与 `build_pptx.py` 顶部 `COLOR_*` 常量同步调整。
- **替换 / 新增图片**：将图片放入 `assets/`，HTML 里用 `<img src="assets/xxx.png">`，PPTX 里用 `add_image_fit(slide, left, top, max_w, max_h, "xxx.png")`。
- **封面元信息**：P01 封面的「课程 / 作者 / 日期」为占位内容，汇报前请替换为真实信息；PPTX 可直接在 PowerPoint 中双击修改，HTML 则改 `index.html` 中 `.cover .meta` 的三个 `<div>`。

---

## 七、已验证产物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `index.html` | 16 页 reveal.js 单文件 PPT | ✅ 已生成 |
| `Shop-Agent汇报.pptx` | 16:9，16 张幻灯片，每页含讲者备注，嵌入 7 张真实图片 | ✅ 已由脚本生成（约 1.2 MB） |
| `assets/diagram-architecture.png` | 系统整体架构图（报告图 7） | ✅ |
| `assets/diagram-tool-calling.png` | Tool Calling UML 时序（报告图 2） | ✅ |
| `assets/diagram-rag-flow.png` | RAG 两阶段流程（报告图 4） | ✅ |
| `assets/diagram-er.png` | 数据库 ER 图（报告图 5） | ✅ |
| `assets/shot-miniapp-login.png` | 微信小程序登录页 | ✅ |
| `assets/shot-rag-result.png` | 小程序 RAG 推荐结果 | ✅ |
| `assets/shot-streamlit.png` | Streamlit 联调页 | ✅ |
| `build_pptx.py` | PPTX 构建脚本（依赖 `python-pptx` + `pillow`） | ✅ 已验证可执行 |

> 构建脚本已经过本地 Python 3 + python-pptx + Pillow 运行验证，生成的 `.pptx` 可直接用 PowerPoint / WPS / Keynote 打开。
