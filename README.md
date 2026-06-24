# 跨境电商选品 Skill

一个 **用户真实问题驱动** 的跨境电商选品优化 Skill。它从公开用户评论、问答、社媒讨论和支持论坛中提取真实痛点，把零散反馈聚合成可验证的产品参数、供应商打样测试项和 Listing 风险约束。

> 核心判断：媒体评测可以做背景，但不能替代真实用户评论。选品优化应该优先回答“用户长期使用中到底抱怨什么，以及这些抱怨能不能转成可验证参数”。

## 项目价值

传统选品调研容易停留在媒体测评、榜单文章和参数整理上。这些信息完整，但不一定代表真实用户长期使用后的痛点。

这个 Skill 重点解决：

- 从公开用户评论中识别高频差评点，而不是只看媒体结论。
- 区分真实用户源和媒体背景源。
- 把用户问题聚类成问题簇，如清洗、噪音、排水、可靠性。
- 在问题簇层输出产品改进参数、供应商测试项和 Listing 避坑建议。
- 用反例样本验证：只有媒体评测时不能通过用户问题审查。

## 工作流

```text
创建品类 profile
-> 采集公开用户评论 / Q&A / 社媒讨论 / 支持论坛
-> 记录 raw_user_quote、evidence_text、user_problem
-> 判断来源是否为真实用户源
-> 检查证据是否可追溯
-> 聚合用户问题簇
-> 输出产品参数、打样测试项、Listing 约束
```

## 作品亮点

- **用户问题优先**：`ecommerce_review`、`ecommerce_qa`、`youtube_comment`、`tiktok_comment`、`support_forum` 等用户源优先。
- **媒体降权**：`expert_review`、`shopping_article`、`trend_article` 只能作为背景材料。
- **轻量采集**：原始证据只保留 13 个核心字段，避免每条评论都重复填写复杂参数。
- **问题簇决策**：产品参数和供应商测试在聚类层生成，不在单条评论层硬写。
- **可复现样例**：包含 golden sample、跨品类样例和媒体-only 反例。
- **无外部依赖运行**：核心评分脚本只使用 Python 标准库。

## 示例输出

以 `portable_ice_maker` 台式制冰机样例为例，报告会输出：

- 采集配额审查
- 用户真实问题 Top 10
- 高频问题簇
- 产品参数 / 供应商测试
- 可疑证据队列

示例问题簇：

| 用户问题簇 | 可转化方向 |
|---|---|
| 清洗/除垢 | 可见水路、可拆触水部件、自动清洁、除垢提醒 |
| 排水 | 避免底部-only 排水，验证满水状态下是否需要搬起机器 |
| 噪音 | 稳定运行 dBA、落冰瞬时 dBA |
| 融化/储冰 | 明确冰篮不是 freezer，验证融化率和融水回流 |
| 可靠性 | 水泵、压缩机、水位传感器、满冰传感器、错误恢复 |

## 目录结构

```text
local-skills/category-scout-reflection/
  可复用的本地 Skill 包，包含说明、模板和评分脚本

examples/portable_ice_maker/
  golden sample：台式制冰机用户问题驱动选品链路

examples/portable_blender/
  第二品类样例：验证 Skill 不依赖制冰机固定答案

examples/media_only_negative/
  反例样例：验证只有媒体资料时不能通过用户问题审查

scripts/
  一键运行、测试和校验脚本

tests/
  回归测试数据
```

## 快速运行

核心脚本只使用 Python 标准库。Fresh clone 后可以先运行 golden sample：

```bash
./scripts/run_real_sample.sh
```

输出位置：

```text
examples/portable_ice_maker/output/
  dashboard.html
  reflection_report.md
  scored_observations.csv
  scored_observations_zh.csv
```

运行核心回归测试和三个样例，不需要安装额外依赖：

```bash
python3 ./scripts/run_skill_tests.py
./scripts/run_real_sample.sh
./scripts/run_blender_sample.sh
./scripts/run_media_only_negative.sh
```

如果要运行包含 Codex Skill manifest 校验的全量检查，需要先安装 PyYAML 到本地依赖目录：

```bash
python3 -m pip install --target .local-python-packages -r requirements.txt
./scripts/run_all_samples.sh
```

也可以只单独运行 manifest 校验：

```bash
PYTHONPATH=.local-python-packages ./scripts/validate_skill.sh
```

生成的 output、本地依赖和 zip 都已在 `.gitignore` 中排除。

如果只想安装到全局或当前 Python 环境：

```bash
python3 -m pip install -r requirements.txt
```

## 新品类脚手架

创建一个新类目的 profile 和轻量 observations 模板：

```bash
python3 scripts/new_category_profile.py \
  --category electric_lunch_box \
  --display-name "Electric Lunch Box" \
  --display-name-zh "电热饭盒" \
  --out examples/electric_lunch_box
```

生成后的 `profile.json` 是中性初稿，需要按目标品类补充关键词、问题维度、供应商测试和 Listing 约束。`observations.csv` 只包含表头和 TODO 示例，不包含固定答案。

## 样例说明

`portable_ice_maker` 是 golden sample，不是 Skill 的默认答案。

当前样例以用户源为主：12 条 ecommerce review/Q&A/YouTube/TikTok/support-forum 类型证据，2 条媒体背景材料。每条原始证据只要求这些核心字段：

- `item_id`
- `source_type`
- `source_name`
- `url`
- `screenshot_path`
- `title`
- `product_or_topic`
- `evidence_text`
- `raw_user_quote`
- `user_problem`
- `problem_dimension`
- `polarity`
- `captured_date`

这些样例数据用于验证流程、字段和报告结构，不代表真实市场结论。真实调研必须替换成可追溯的公开 URL 或截图，并保留采集日期和 raw quote。

## 面试讲法

> 这是一个用户问题驱动的跨境电商选品优化 Skill。对任意目标产品，先建立 category profile，再轻量记录公开用户评论、问答和社媒讨论的核心证据。Skill 负责判断来源优先级、检查证据是否可追溯、把评论聚合成高频问题簇，并在问题簇层输出可验证产品参数和供应商打样测试项。媒体评测只能做背景，不能作为主证据。制冰机只是 golden sample，不能当成跨品类答案模板。

## 边界

- 不包含竞品后台数据。
- 不绕平台反爬。
- 不声称自动判断最终选品结果。
- 不把媒体评测当成真实用户痛点主证据。
- 不上传本地 Python 依赖目录或生成物。
