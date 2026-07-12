# 安装说明

推荐把这个 skill 当成"先安装，再补依赖，再开始用"的工具，而不是只复制仓库文件。

## 1. 安装 skill

推荐全局安装：

```bash
npx skills add https://github.com/Eliott-lzh0610/english-vocabulary-skills --skill CET --yes --global
```

如果你只想安装到当前项目，可以去掉 `--global`：

```bash
npx skills add https://github.com/Eliott-lzh0610/english-vocabulary-skills --skill CET --yes
```

安装完成后，重启 Codex / Claude Code，让新 skill 生效。

## 2. 找到安装后的 skill 目录

`npx skills add ...` 安装的是"skill 副本"，不是直接在这个仓库目录里运行。

常见位置：

- Codex：`%USERPROFILE%\\.codex\\skills\\`
- Claude Code：通常也会放在自己的用户 skill 目录；如果你不确定，请直接在本机搜索 `CET`

如果你是全局安装到 Codex，通常直接进入下面目录即可：

```powershell
cd $env:USERPROFILE\.codex\skills\CET
```

## 3. 安装 Python 依赖

安装完成后，请在"安装后的 skill 目录"里补依赖，而不是在这个 GitHub 仓库根目录里执行。

```powershell
cd $env:USERPROFILE\.codex\skills\CET
python -m pip install -r requirements.txt
```

如果你不是装在 Codex 默认目录，请把上面的路径替换成你自己的实际安装位置。

## 4. 额外环境准备

通常还需要：

- Python 3.10 或更高版本

依赖的第三方库（`requirements.txt` 已包含）：

- `pdfplumber` — 考纲 PDF 解析
- `openpyxl` — 高考 3500 词 Excel 读取
- `spellchecker` — 拼写校验

## 5. 准备输入文件

在开始使用前，你需要准备以下输入文件（不包含在仓库中）：

| 文件 | 用途 | 来源 |
|---|---|---|
| 考纲 PDF | 四六级词表提取 | 《全国大学英语四、六级考试大纲（2016 年修订版）》 |
| 3500.xlsx | 高考词汇参照过滤 | 教育部 2019 年高考英语考纲 |

将这两个文件放到方便引用的位置即可，脚本通过命令行参数指定路径。

## 6. 推荐的第一次使用顺序

如果你是第一次用，建议按这个顺序来：

1. 先用 `extract_syllabus` 从考纲 PDF 提取 CET4/CET6 词表
2. 再用 `filter_cet4` 过滤出四级独有词
3. 然后 `lookup_notes` 生成带释义的 MD 笔记
4. 按需使用 `export_notes` 导出或 `init_vault` 导入 Obsidian
5. 最后用 `validate_notes` 做一次格式校验

## 7. 平台建议

- Windows / macOS / Linux 均可
- 不需要浏览器，纯命令行 Python 脚本
- 有道词典查询需要网络连接

## 8. 读哪个文档

安装完以后：

- 工作流和命令说明：看 `CET/SKILL.md`
- 各脚本的详细参数：也在 `SKILL.md` 里

这个 `INSTALL.md` 只负责"怎么装、装完去哪里、首次怎么起步"，具体工作流细节都在 `SKILL.md` 里。
