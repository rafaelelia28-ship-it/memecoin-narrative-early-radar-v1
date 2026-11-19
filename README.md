# Memecoin Narrative Early Radar — V1

Starter project for a low-cost, multi-chain/global narrative research radar.

## What V1 does
- Polls selected public RSS feeds every 30 minutes using GitHub Actions.
- Extracts article headlines, summaries, publication dates and source URLs.
- Groups items into broad narrative clusters using transparent keyword rules.
- Stores source items and narrative summaries in Supabase.
- Publishes a static dashboard with GitHub Pages.
- Refreshes dashboard data every 5 minutes while open.

**Important:** V1 is a working foundation, not a validated prediction engine. RSS coverage is incomplete; keyword grouping can misclassify stories. Social platforms such as X/TikTok are not scraped. Market adoption is not yet connected. The dashboard labels its data and scores as preliminary.

## Architecture
GitHub Actions (scheduled Python collector) → RSS feeds → Supabase (Postgres + REST) → GitHub Pages dashboard.

## Setup

### 1. Create Supabase project
1. Open https://supabase.com/dashboard and create a new project.
2. Save the database password privately.
3. Wait until the project is ready.
4. Open **SQL Editor → New query**.
5. Copy all of `supabase/schema.sql` into the editor and click **Run**.

### 2. Get Supabase credentials
In Supabase open **Project Settings → API** (or API Keys):
- Project URL
- `anon` / publishable key
- `service_role` / secret key

Never put the service role key in the dashboard or commit it to GitHub. It belongs only in GitHub Actions Secrets. Do not share it in chat.

### 3. Put this project on GitHub
1. Create a new repository at https://github.com/new.
2. Name it `memecoin-narrative-early-radar`.
3. For easiest setup, choose **Public** (GitHub Pages on private repositories may require a paid plan depending on your account).
4. Do not add a README/license/gitignore because this ZIP already contains them.
5. Extract this ZIP on your computer.
6. In the new GitHub repository choose **Add file → Upload files**.
7. Upload the contents of the extracted folder (including `.github`), then commit.

### 4. Add GitHub Actions secrets
In your repository open **Settings → Secrets and variables → Actions → New repository secret**.
Create:
- `SUPABASE_URL` = your Supabase Project URL
- `SUPABASE_SERVICE_ROLE_KEY` = your service role / secret key

Do not add these values to source code or send them to anyone.

### 5. Configure dashboard
Open `dashboard/config.js` in GitHub and replace:
- `YOUR_SUPABASE_PROJECT_URL`
- `YOUR_SUPABASE_ANON_KEY`

Use only the public anon/publishable key here. Commit the change.

### 6. Enable GitHub Pages
1. Repository **Settings → Pages**.
2. Under Build and deployment, choose **GitHub Actions**.
3. Open the **Actions** tab and run `Deploy dashboard` (or push a new commit).
4. When successful, GitHub shows the Pages URL, usually `https://YOUR-USERNAME.github.io/memecoin-narrative-early-radar/`.

### 7. Run the collector once
1. Open **Actions → Collect narrative signals**.
2. Choose **Run workflow → Run workflow**.
3. Wait for it to finish. Check the logs for `Inserted/updated ...`.
4. Open the dashboard URL.

The scheduled collector runs every 30 minutes. GitHub may delay scheduled workflows, especially during busy periods. The daily report is refreshed once per UTC date and can be viewed in the dashboard.

## Data sources included
- CoinDesk RSS
- De​​crypt RSS
- TechCrunch RSS
- The Verge RSS
- BBC World RSS
- Hacker News RSS

Feeds may change, rate-limit or become unavailable. The collector logs failures and continues with the remaining sources.

## Scoring notes
The initial score is a heuristic based on recent item count, number of distinct sources and freshness. It is not a measure of token returns, nor a buy/sell signal. A narrative is marked "Emerging" only as a research label. Verify original sources and market data independently.

## Troubleshooting
- `relation does not exist`: run `supabase/schema.sql` again in SQL Editor.
- `Invalid API key`: check the URL/key and ensure the service role key is in GitHub Secrets.
- Dashboard says "No data": run the collector manually and check the Actions logs.
- Dashboard cannot load data: check `dashboard/config.js`, RLS policies, and browser console.
- GitHub Pages 404: confirm Pages source is GitHub Actions and the deploy workflow succeeded.

## Next upgrades
1. Reddit API integration (official API credentials).
2. Google Trends signal history.
3. Cross-platform social velocity and source-origin tracing.
4. DEX Screener / GeckoTerminal market adoption scanner.
5. Telegram notifications and a stronger AI-assisted clustering layer.
