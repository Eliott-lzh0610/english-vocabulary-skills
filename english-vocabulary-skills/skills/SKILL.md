---
name: CET
description: Complete CET-4/6 vocabulary pipeline: extract from syllabus PDF, filter against Gaokao, generate Collins dictionary notes, and manage Obsidian vault.
---

# CET Vocabulary Pipeline

CET-4/6 英语词汇完整工作流。

## 前置依赖

```bash
pip install -r requirements.txt
```

## 工作流

```
考纲PDF ──→ extract_syllabus ──→ CET4/CET6 TXT
                                      │
                             filter_cet4 (3500.xlsx)
                                      │
                                      ▼
                               CET4-exclusive TXT
                                      │
                             lookup_notes (有道Collins)
                                      │
                                      ▼
                               MD 笔记 (output/notes/)
                                      │
                             init_vault ──→ Obsidian 库
                                      │
                             (手动编辑A字母)
                                      │
                             validate_notes ──→ 校验报告
```

## 命令

### 1. extract_syllabus — 考纲提取

```powershell
python scripts\extract_syllabus.py "<考纲PDF>" -o ./output/syllabus
```

从《全国大学英语四、六级考试大纲》提取词表，按 CET4/CET6 分目录输出 TXT。

| 参数 | 说明 |
|---|---|
| `pdf_path` | 考纲 PDF 路径 |
| `-o --output-dir` | 输出目录（默认 output/syllabus） |
| `--start-page` | 词表起始页（默认 21） |

### 2. filter_cet4 — 四级独有词过滤

```powershell
python scripts\filter_cet4.py --cet4-dir ./output/syllabus/CET4 --cet6-dir ./output/syllabus/CET6 --xlsx "3500.xlsx" -o ./output/cet4-exclusive
```

用 3500.xlsx（高考考纲）过滤四级独有词：
- xlsx 三列全量比对
- 词频过滤初等词
- 同形异义词合并
- G→空格修复

### 3. lookup_notes — 有道查词生成笔记

```powershell
python scripts\lookup_notes.py --txt-dir ./output/syllabus/CET4 -o ./output/notes/CET4
```

逐词查询有道词典（Collins 优先），生成 MD 笔记：
- 精确词性（V-T/V-I/N-COUNT/ADJ/ADV）
- 中文释义 + 搭配介词（`+to`/`+with`）
- 双语例句
- 待处理清单

### 4. export_notes — 导出初版笔记

```powershell
python scripts\export_notes.py --notes-dir ./output/notes --target "<目标路径>"
```

将自动生成的 MD 笔记（初版，未人工编辑）复制到指定本地目录。不依赖 Obsidian。

### 5. init_vault — Obsidian 库初始化

```powershell
python scripts\init_vault.py --vault-dir "<库路径>" --notes-dir ./output/notes
```

创建 Obsidian 词库，导入生成的 MD 笔记。

### 6. validate_notes — 格式校验

```powershell
python scripts\validate_notes.py --notes-dir ./output/notes/CET4
```

校验词条格式、例句格式、编号连续性、跨文件重复。

## 输入文件

| 文件 | 用途 | 来源 |
|---|---|---|
| 考纲 PDF | 四六级词表提取 | 《全国大学英语四、六级考试大纲（2016年修订版）》 |
| 3500.xlsx | 高考词汇参照 | 教育部 2019 年高考英语考纲 |

## 输出结构

```
output/
├── syllabus/
│   ├── CET4/  (A-W TXT, 807 四级独有词)
│   └── CET6/  (A-Z TXT, 1263 六级词)
├── notes/
│   ├── CET4/  (A-W MD, 带释义+例句)
│   └── CET6/  (A-Z MD)
└── dict_cache.json
```
