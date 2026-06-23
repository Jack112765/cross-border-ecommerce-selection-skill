---
name: category-scout-reflection
description: Build reusable user-problem-first product research workflows for cross-border ecommerce. Use when collecting public customer reviews, ecommerce Q&A, Reddit threads, YouTube/TikTok comments, or support forum signals for any product category; separating real user evidence from media background; clustering problems into product parameters, supplier tests, and listing guardrails.
---

# Category Scout Reflection

Use this skill to turn any product category into a lightweight evidence workflow:

```text
Define category profile -> Collect user evidence -> Check traceability
-> Cluster user problems -> Produce product-selection actions
```

Core rules:

- Start from the user's product/category. Do not default to a bundled example category.
- Treat bundled examples as fixtures for validation only, not as product recommendations or answer templates.
- Real user comments, Q&A, Reddit, video comments, and support forums are primary evidence.
- Media reviews, shopping articles, and trend articles are background only.
- Raw evidence rows stay lightweight; product parameters and supplier tests belong in problem-cluster summaries.
- A primary evidence row needs a concrete URL or screenshot, plus a copied raw user quote.

Create or adapt a profile before scoring a new product:

- Copy `assets/category_profile_template.json`.
- Set `category`, `display_name`, `display_name_zh`, and `search_need` for the requested product.
- Replace category keywords, exclude keywords, problem dimensions, improvement rules, supplier tests, and listing guardrails with product-specific values.
- Keep source quotas product-neutral unless the user gives a reason to change them.

Required observation columns:

```text
item_id,source_type,source_name,url,screenshot_path,title,product_or_topic,
evidence_text,raw_user_quote,user_problem,problem_dimension,polarity,captured_date
```

Optional fields such as `problem_severity`, `frequency_signal`, `parameter_to_verify`, `supplier_test`, `brand`, `product_model`, and count fields may be added during review, but are not required for raw collection.

Run the scoring script with the product-specific profile and observations:

```bash
python3 scripts/category_scout_reflection.py \
  --profile path/to/category_profile.json \
  --observations path/to/search_observations.csv \
  --out /tmp/category-scout-output
```

Review outputs:

- `reflection_report.md`: quota audit, Top 10 user problems, problem clusters, product parameters/supplier tests, suspicious evidence queue.
- `scored_observations.csv`: machine-readable scored evidence.
- `scored_observations_zh.csv`: Chinese review table.
- `dashboard.html`: visual evidence review page.

Bundled examples live in the project-level `examples/` directory:

- `examples/portable_ice_maker/`: golden sample for an end-to-end passing report.
- `examples/portable_blender/`: cross-category fixture for checking the workflow is not tied to ice makers.
- `examples/media_only_negative/`: negative fixture proving media-only datasets fail the evidence gate.
- Use examples only for validation, demos, or regression checks. For a real user request, build a fresh profile and evidence table for that product.

Read `references/manual-search-guide.md` before collecting a new category, and `references/reflection-model.md` before changing scoring, quotas, or rejection behavior.
