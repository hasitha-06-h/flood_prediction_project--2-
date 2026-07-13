# Deploying to Render

Render deploys directly from a Git repository (GitHub, GitLab, or
Bitbucket), so the one step I can't do for you is pushing this code to a
repo under your account — that needs your credentials. Everything else
below is exactly what I tested locally.

## What I verified

I ran Render's actual build and start commands against this project, not
just a guess at what "should" work:

- **Build command:** `pip install -r requirements.txt && python train_model.py`
  → completed cleanly, produced `model/model.pkl`, `model/scaler.pkl`, `model/metadata.json`
- **Start command:** `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
  → started cleanly, and `/`, `/predict` (GET + POST), and `/history` all returned HTTP 200

The only thing I can't verify from this sandbox is Render's own build
container and your live `onrender.com` URL, since I have no network access
to Render or your GitHub account.

## Step 1 — Push the project to GitHub

```bash
cd flood_prediction_project
git init
git add .
git commit -m "Flood prediction Flask app"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## Step 2 — Create the Render service

**Option A: Blueprint (uses the included `render.yaml`, no manual form-filling)**

1. Go to https://dashboard.render.com → **New** → **Blueprint**
2. Connect your GitHub account if you haven't already, then select the repo
3. Render reads `render.yaml` and pre-fills the build/start commands and plan automatically
4. Click **Apply** — Render creates and deploys the service

**Option B: Manual Web Service**

1. Go to https://dashboard.render.com → **New** → **Web Service**
2. Connect the repo
3. Fill in:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt && python train_model.py`
   - **Start Command:** `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
   - **Instance Type:** Free (or Starter for always-on, no cold starts)
4. Click **Create Web Service**

Render assigns a live URL like `https://rising-waters-flood-prediction.onrender.com`
as soon as the first build finishes. Every subsequent `git push` to the
connected branch auto-redeploys.

## Free tier limitations to know about (not bugs in this app)

- **Cold starts:** Render's free instances spin down after 15 minutes of
  inactivity and take ~30–60 seconds to wake on the next request. Upgrade
  to the Starter plan ($7/mo) if you need it always-on for a demo.
- **No persistent disk:** the free tier's filesystem resets on every
  redeploy/restart, so `history.db` (SQLite) will reset too. For history
  that survives restarts, add a free Render Postgres instance and point
  `app.py`'s `DB_PATH`/connection logic at it instead of SQLite — that's a
  small, contained change if you want it done.

## After deploying

Visit your `onrender.com` URL and confirm:
1. Home page loads and shows the model name + accuracy
2. `/predict` form submits and returns a flood/no-flood result
3. `/history` shows the prediction you just made

If a build fails, Render's dashboard shows the full build log — the most
common cause is a typo in the start command or a missing package in
`requirements.txt`, neither of which apply here since both were tested.
