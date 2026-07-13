# Deploying to IBM Cloud (Code Engine)

This matches the "Deploy to Cloud (IBM Cloud)" step in the architecture
diagram. IBM Cloud's current recommended path for a containerized app like
this is **Code Engine** (serverless containers) rather than the older Cloud
Foundry buildpacks. These steps use the container image approach with the
included `Dockerfile`.

## Prerequisites

- An IBM Cloud account: https://cloud.ibm.com/registration
- IBM Cloud CLI installed: https://cloud.ibm.com/docs/cli
- Docker installed locally (only needed if you build the image yourself instead of letting Code Engine build it from source)

## Option A — Let Code Engine build directly from source (simplest)

No local Docker required; Code Engine builds the image from your
`Dockerfile` in the cloud.

```bash
# 1. Log in
ibmcloud login --sso            # or: ibmcloud login -u <user> -p <pass>
ibmcloud target -g Default       # select your resource group

# 2. Install/select the Code Engine plugin
ibmcloud plugin install code-engine

# 3. Create (or select) a Code Engine project
ibmcloud ce project create --name rising-waters-project
ibmcloud ce project select --name rising-waters-project

# 4. Push your code to a Git repo Code Engine can read (e.g. GitHub), then:
ibmcloud ce application create \
  --name rising-waters \
  --build-source https://github.com/<your-username>/<your-repo> \
  --strategy dockerfile \
  --port 8080 \
  --min-scale 1 \
  --max-scale 2 \
  --cpu 1 --memory 2G

# 5. Get the public URL
ibmcloud ce application get --name rising-waters
```

The output includes a `URL` field — that's your live application.

## Option B — Build the image locally and push to IBM Container Registry

```bash
# 1. Log in and target a region
ibmcloud login --sso
ibmcloud cr region-set us-south         # pick your region
ibmcloud cr login

# 2. Create a namespace (once)
ibmcloud cr namespace-add rising-waters-ns

# 3. Build and push the image
docker build -t us.icr.io/rising-waters-ns/flood-app:latest .
docker push us.icr.io/rising-waters-ns/flood-app:latest

# 4. Create the Code Engine project + app from the pushed image
ibmcloud ce project create --name rising-waters-project
ibmcloud ce project select --name rising-waters-project

ibmcloud ce registry create --name my-icr-secret \
  --server us.icr.io \
  --username iamapikey \
  --password <YOUR_IBM_CLOUD_API_KEY>

ibmcloud ce application create \
  --name rising-waters \
  --image us.icr.io/rising-waters-ns/flood-app:latest \
  --registry-secret my-icr-secret \
  --port 8080 --min-scale 1

# 5. Get the URL
ibmcloud ce application get --name rising-waters
```

## Redeploying after changes

```bash
# Option A (source-based): just push new commits and re-run:
ibmcloud ce application update --name rising-waters --build-source <repo-url>

# Option B (image-based): rebuild, push, then:
docker build -t us.icr.io/rising-waters-ns/flood-app:latest .
docker push us.icr.io/rising-waters-ns/flood-app:latest
ibmcloud ce application update --name rising-waters \
  --image us.icr.io/rising-waters-ns/flood-app:latest
```

## Important: prediction history is not persistent on Code Engine

Code Engine containers are stateless/ephemeral — the `history.db` SQLite
file will reset whenever the container restarts or scales. For a real
production deployment where history must survive restarts, swap the SQLite
calls in `app.py` for a managed database such as **IBM Cloudant** or
**IBM Db2 on Cloud**, both of which can be provisioned and bound to the
Code Engine app via `ibmcloud ce application bind`. This is a scope choice,
not a bug — the app works correctly as-is for demos and single-session use.

## Local test before deploying (recommended)

If you have Docker installed on your machine:

```bash
docker build -t flood-app .
docker run -p 8080:8080 flood-app
# visit http://localhost:8080
```

I was unable to run `docker build` myself in this sandbox (no Docker
daemon available here), but I did verify the exact production entrypoint
the Dockerfile uses — `gunicorn -w 2 -b 0.0.0.0:$PORT app:app` — runs
cleanly end-to-end, including form validation, prediction, and history
routes. Please still do a local `docker build`/`docker run` pass yourself
before pushing to IBM Cloud, since I can't verify the Docker layer itself
from here.
