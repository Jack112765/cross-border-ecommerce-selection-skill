# Reflection Model

The reflection layer scores whether evidence can support product-selection optimization. It should not reward a row merely for matching category keywords.

## Core Score

Each row is scored on five 20-point dimensions:

| Dimension | Points | Meaning |
|---|---:|---|
| User-source credibility | 20 | Primary sources include ecommerce reviews, Q&A, Reddit, YouTube/TikTok comments, and support forums. |
| Problem specificity | 20 | `user_problem` names a concrete complaint, question, risk, or unmet expectation. |
| Traceability | 20 | The row has a concrete URL or screenshot and `raw_user_quote` appears inside `evidence_text`. |
| Repetition | 20 | Repetition is inferred from optional counts or from multiple rows in the same `problem_dimension`. |
| Product-action fit | 20 | The problem can map to a product parameter, supplier test, listing guardrail, or manual review action. |

## Penalties

Down-rank or reject rows when:

- The source is media/background rather than a user source.
- The row has no raw user quote.
- The row has no concrete URL or screenshot.
- The URL is only a search results page.
- `raw_user_quote` does not appear in `evidence_text`.
- The evidence is generic praise only.
- The content is off-category or matches exclude keywords.

## Frequency

Frequency should come from data, not only a hand-written label.

- `single`: one evidence row.
- `repeated`: three or more rows or count signals.
- `many`: eight or more rows, or evidence spanning several products/platforms.

If optional count fields are absent, the script uses the number of rows in the same `problem_dimension`.

## Problem Clusters

Raw observation rows only record user evidence. Product decisions are generated at the cluster layer:

```text
problem_dimension,evidence_ids,frequency,parameter_to_verify,supplier_test
```

Cluster-level parameters may come from profile rules, optional review fields, or manual review. Do not force every raw comment row to repeat `supplier_test` or `parameter_to_verify`.

## Source Quota Audit

The report should fail when:

- There are too few real user-problem rows.
- Negative/question/risk rows are too few.
- Media/background rows exceed the configured ratio.
- Distinct user sources, platforms, products, or top-problem support are below configured thresholds.

Media rows can remain in the dataset as background, but they cannot satisfy user-problem quotas.
