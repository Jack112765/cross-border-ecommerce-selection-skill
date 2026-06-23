# Manual Search Guide

Use this guide when collecting observations for `category_scout_reflection.py`.

## Collection Order

Collect user-problem sources before media sources:

1. Ecommerce reviews: low-star reviews, recent reviews, verified purchase reviews.
2. Ecommerce Q&A: buyer questions about failures, size, compatibility, cleaning, noise, safety.
3. Reddit/YouTube/TikTok comments: real usage friction and repeated complaints.
4. Support forums: troubleshooting, returns, warranty, recurring defects.
5. Expert reviews and shopping articles: only after user-problem rows exist.

## Source Types

Primary user sources:

- `ecommerce_review`
- `ecommerce_qa`
- `reddit_thread`
- `youtube_comment`
- `tiktok_comment`
- `support_forum`

Secondary background sources:

- `expert_review`
- `shopping_article`
- `trend_article`
- `news_recall`

Do not use generic `review` or `social`. Pick the precise source type so the scoring layer can distinguish customer pain from media background.

## Required Fields

Each row must include:

- `item_id`: stable evidence ID.
- `source_type`: one of the supported source types.
- `source_name`: platform, publisher, subreddit, channel, or forum name.
- `url`: concrete review, Q&A, thread, video, or forum URL when available.
- `screenshot_path`: local screenshot path when the source is unstable or the evidence is a video/social comment.
- `title`: page, thread, video, product, or review collection title.
- `product_or_topic`: product name or topic.
- `evidence_text`: copied source text that includes the raw quote.
- `raw_user_quote`: the exact short user quote used for audit.
- `user_problem`: what the customer complains about or asks.
- `problem_dimension`: cleaning, noise, reliability, melting, size, safety, etc.
- `polarity`: positive, negative, mixed, risk, question, unknown.
- `captured_date`: date collected.

Optional review fields include `problem_severity`, `frequency_signal`, `frequency_evidence`, `requested_fix`, `parameter_to_verify`, `supplier_test`, `brand`, `product_model`, and count fields. Add them during second-pass review only when useful.

## Collection Rules

- For a category review, collect at least 10 user-problem rows before relying on media.
- Include at least 7 negative/question/risk rows for product optimization.
- Use at least 3 distinct user sources, not one article or one review page only.
- Keep off-category rows when they reveal query pollution; the scoring penalty helps refine search.
- Do not turn a media reviewer's observation into `user_problem`; keep it secondary.
- Do not invent frequency. The script can infer repetition from multiple rows in the same `problem_dimension`.
- Preserve the original evidence text enough that a reviewer can audit the extraction.
- Keep supplier tests and product parameters at the problem-cluster layer; do not repeat them on every raw comment row.
