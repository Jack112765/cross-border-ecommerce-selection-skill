# Category Scout Reflection

一个面向跨境电商选品优化的半自动化 Skill，核心是“真实用户问题优先”。它应该复用于任意具体产品类目，而不是记住某个类目的答案。

它不是竞品后台数据抓取器，也不是全自动选品系统。它做的是：

```text
为目标产品创建 category profile
-> 人工/半自动搜索公开用户评论、问答、社媒讨论
-> 记录 URL、raw_user_quote、evidence_text 和 user_problem
-> 判断来源是否为真实用户源
-> 用户问题具体、重复、可转产品参数则加分
-> 媒体评测/购物文章降级为背景
-> 把用户问题聚成问题簇
-> 在问题簇层输出产品参数、打样测试项和 Listing 约束
-> 后续可沉淀到 RAG 知识库
```

## 目录

```text
local-skills/category-scout-reflection/
  可复用的本地 Skill 包，包含说明、模板和评分脚本

examples/portable_blender/
  第二品类样例，用于验证 Skill 不依赖制冰机这个 golden sample

examples/portable_ice_maker/
  台式制冰机 golden sample，用于展示从真实用户问题到产品参数、供应商测试和 Listing 约束的完整链路

examples/media_only_negative/
  反例样例，用于证明只有媒体评测/购物文章时不会通过真实用户问题审查

scripts/
  一键运行、测试和校验脚本

tests/
  回归测试数据
```

## 快速开始

核心脚本只使用 Python 标准库，不安装依赖也可以运行 golden sample：

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

其中 `dashboard.html`、`reflection_report.md` 和 `scored_observations_zh.csv` 面向中文展示；`scored_observations.csv` 保留英文机器字段，方便后续接 RAG 或二次脚本。

## 测试

Fresh clone 后建议直接跑全量检查，验证脚本、正例、跨品类样例、媒体反例和 Skill manifest 都可复现：

```bash
./scripts/run_all_samples.sh
```

如果要运行官方 Skill 校验脚本，需要 PyYAML：

```bash
python3 -m pip install -r requirements.txt
```

或者安装到本地目录：

```bash
python3 -m pip install --target .local-python-packages -r requirements.txt
```

然后验证：

```bash
PYTHONPATH=.local-python-packages ./scripts/validate_skill.sh
```

## 样例数据说明

制冰机是 golden sample，不是 Skill 的默认答案：

```text
portable_ice_maker
```

当前 `examples/portable_ice_maker` 以用户源为主：12 条 ecommerce review/Q&A/YouTube/TikTok/support-forum 类型证据，2 条媒体背景材料。每条原始证据只要求 13 个核心字段：

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

报告会把清洗/除垢、排水、噪音、融化/储冰、可靠性、尺寸和安全聚合成问题簇，再在簇层输出 `parameter_to_verify` 和 `supplier_test`。媒体材料只做背景参数参考。

数据文件：

```text
examples/portable_ice_maker/observations_2026-06-23.csv
examples/portable_ice_maker/profile.json
```

`examples/portable_blender` 是第二品类 fixture，用来验证同一套流程能迁移到便携榨汁杯。它不应该复用制冰机的问题维度、供应商测试或 Listing 约束。

`examples/media_only_negative` 是反例 fixture，用来验证只有媒体评测/购物文章时报告必须不通过，媒体行只能作为背景来源。

这些 `example.com` 数据是 fixture，只验证流程、字段和报告结构，不代表真实市场结论。真实调研必须替换成可追溯的公开 URL 或截图，并保留采集日期和 raw quote。

## 新类目脚手架

创建一个新类目的 profile 和轻量 observations 模板：

```bash
python3 scripts/new_category_profile.py \
  --category electric_lunch_box \
  --display-name "Electric Lunch Box" \
  --display-name-zh "电热饭盒" \
  --out examples/electric_lunch_box
```

生成后的 `profile.json` 是中性初稿，必须按目标品类补充关键词、问题维度、供应商测试和 Listing 约束；`observations.csv` 只包含表头和 TODO 示例，不包含固定答案。

## 面试讲法

> 这是一个用户问题驱动的跨境选品优化 Skill。对任意目标产品，先建立 category profile，再轻量记录公开用户评论、问答和社媒讨论的核心证据。Skill 负责判断来源优先级、检查证据是否可追溯、把评论聚合成高频问题簇，并在问题簇层输出可验证产品参数和供应商打样测试项。媒体评测只能做背景，不能作为主证据。制冰机只是 golden sample，不能当成跨品类答案模板。

## 不包含

- 不包含竞品后台数据
- 不绕平台反爬
- 不上传本地 Python 依赖目录
- 不声称自动判断最终选品结果
- 不把媒体评测当成真实用户痛点主证据
