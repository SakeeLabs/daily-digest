# Data policy

This project follows Reddit's Data API Terms and Responsible Builder Policy.

**Purpose.** A private daily summary for one person. Non-commercial.

**What is collected.** Public post metadata only: post ID, subreddit, title, score, comment count, link, creation time, flair, and up to 280 characters of post text. No user profiles, private messages, or personal data. NSFW posts are skipped.

**Retention.** Stored data is kept for at most 30 days, then deleted automatically on the next run.

**Deleted and removed content.** On every run, previously stored posts are re-checked through `/api/info`. Posts that were deleted by their author or removed by moderators or Reddit are purged. With one run per day, this happens well within 48 hours.

**Storage.** Data stays in the owner's private storage. It is never committed to this public repository (`out/` is git-ignored) and never published.

**Sharing.** No data is sold, licensed, shared with third parties, or republished.

**AI.** Reddit data is never used to train or fine-tune any AI model. Summaries are generated per run from the stored metadata and link back to the original posts.

**Credentials.** API credentials live only in environment variables or CI secrets, never in code or commits.

**Changes.** Any change to what is collected will be reflected here first.
