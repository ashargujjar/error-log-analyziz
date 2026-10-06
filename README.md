# Error Log Analyzer

AI-powered error log ingestion, classification, analysis, and review dashboard.

This project accepts raw error logs from applications, stores them as pending work, extracts structured error data with an LLM, runs selected analyzer agents in LangGraph, aggregates the findings, and shows the result in a React dashboard for human review.

## Current Architecture

```text
Application / SDK / curl
        |
        | POST /errors
        | Authorization: Bearer <api_key>
        | body = raw error log text
        v
FastAPI backend
        |
        | save raw payload
        | status = pending
        v
MongoDB errors collection
        |
        | background processing
        v
LLM structured extraction
        |
        | errorType, messages, files, traces, description
        v
LangGraph workflow
        |
        | supervisor_router selects needed analyzers
        v
Parallel analyzer nodes
        |
        | code_analyzer
        | database_analyzer
        | infrastructure_analyzer
        | external_api_analyzer
        v
Aggregator node
        |
        | title, severity, confidence, impact, risks, recommendation
        v
MongoDB updated record
        |
        | status = processed
        | approval = pending
        v
React dashboard
```

## Implemented So Far

### Backend

The backend is built with FastAPI.

Implemented routes:

```text
GET  /health
GET  /auth/github/login
GET  /auth/github/callback
POST /auth/logout
POST /api-keys
GET  /api-keys
DELETE /api-keys/{key_id}
POST /errors
GET  /errors
GET  /errors/{error_id}
```

The `POST /errors` endpoint accepts raw error log text. It does not expect structured JSON from the sender.

Example:

```bash
curl -X POST http://127.0.0.1:8000/errors \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: text/plain" \
  --data-binary "MongoDB connection refused at server startup"
```

### Error Storage

Each error log is saved first as pending.

Main fields stored in MongoDB:

```text
payload              raw error log sent by user/app
payload_content_type original request content type
status               pending | processing | processed | failed
error                structured error extracted by AI
analysis             LangGraph analyzer and aggregator result
incident             final aggregated incident summary
approval             pending | approved
error_message        processing failure message, if any
attempts             processing attempt count
created_at
updated_at
processing_started_at
processed_at
```

Important behavior:

```text
Raw log received -> status = pending
Background worker starts -> status = processing
AI analysis succeeds -> status = processed
AI analysis fails -> status = failed
Human approval is still pending by default
```

### AI Processing

The backend extracts structured data from the raw log first.

Then the structured error is passed into LangGraph.

Supported error classes:

```text
code_error
database_error
network_error
configuration_error
authentication_error
rate_limit_error
dependency_error
infrastructure_error
external_api_error
unknown
```

### LangGraph Workflow

The workflow uses a supervisor router plus selected parallel analyzers.

```text
START
  |
  v
supervisor_router
  |
  | selects only relevant analyzers
  v
parallel analyzers
  |
  v
aggregator
  |
  v
END
```

Analyzer nodes implemented:

```text
Code Analyzer
Database Analyzer
Infrastructure Analyzer
External API Analyzer
```

The supervisor router does not directly create the final answer. It decides which analyzer nodes should run.

The aggregator creates the final incident schema:

```text
title
severity
ai_confidence_score
approval
description
impact
risks
recommendation
traces_to_check
primary_analyzer
```

### Code Analyzer

The Code Analyzer checks:

```text
errorType and code evidence
files, lines, functions, classes, stack traces
likely code problem
recommended action
```

It can optionally use GitHub repository source context when the structured error contains repository/file information and a valid GitHub access token is available.

### Database Analyzer

The Database Analyzer checks:

```text
MongoDB, PostgreSQL, MySQL, Redis, and other databases
connection failures
query errors
schema problems
migrations
transactions
indexes
timeouts
database authentication
database availability
```

### Infrastructure Analyzer

The Infrastructure Analyzer checks:

```text
server crashes
containers
Kubernetes
deployment failures
CPU or memory exhaustion
disk full
host availability
cloud resources
load balancers
service restarts
environment failures
```

### External API Analyzer

The External API Analyzer checks:

```text
GitHub API
Stripe API
AWS API
OpenAI or DeepSeek API
HTTP 401, 403, 404, 429, 500
provider timeouts
invalid API keys
rate limits
third-party outages
webhook failures
```

## Frontend

The frontend is a React + Vite dashboard.

Implemented frontend features:

```text
GitHub login redirect handling
API key creation
API key listing
API key revocation
real error log loading from GET /errors
pending, processing, processed, and failed status display
AI incident summary display
raw log evidence display
impact, risks, recommendation, and traces display
history page
detail page
```

The frontend no longer depends on mock incidents for the main dashboard flow.

## JavaScript SDK

A first JavaScript SDK exists in:

```text
sdk/js
```

It provides:

```text
ErrorLogClient
capture(rawLog)
captureException(error)
captureAndForget(rawLog)
captureExceptionAndForget(error)
installGlobalHandlers()
flush()
shutdown()
```

Example:

```js
import { ErrorLogClient } from "@error-log-analyzer/js-sdk";

const client = new ErrorLogClient({
  apiKey: process.env.ERROR_LOG_API_KEY,
  endpoint: "http://127.0.0.1:8000/errors",
});

await client.capture("raw server crash log");
await client.captureException(new Error("Database crashed"));
```

The SDK sends logs as plain text:

```text
POST /errors
Authorization: Bearer <api_key>
Content-Type: text/plain
```

## Authentication Model

There are two authentication paths:

```text
Dashboard users:
GitHub OAuth session cookie

Log senders:
API key using Authorization: Bearer <api_key>
```

The dashboard uses GitHub OAuth.

Applications and SDKs use API keys.

## GitHub Integration Status

Implemented:

```text
GitHub OAuth login
GitHub user session
encrypted GitHub access token storage
optional token access for analyzer source lookups
```

Not completed yet:

```text
human approval endpoint
frontend approval button connected to backend
GitHub issue creation after approval
GitHub issue URL saved back to MongoDB
```

## Run Locally

### Backend

```bash
cd backend
python -m uvicorn main:app --reload
```

Backend runs on:

```text
http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend
npm run dev
```

Frontend runs on:

```text
http://127.0.0.1:5173
```

### JavaScript SDK Check

```bash
cd sdk/js
node --check src/index.js
```

## Environment Variables

Backend environment example:

```text
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=error_log_analyzer
FRONTEND_URL=http://127.0.0.1:5173

GITHUB_CLIENT_ID=your-github-oauth-client-id
GITHUB_CLIENT_SECRET=your-github-oauth-client-secret
GITHUB_REDIRECT_URI=http://127.0.0.1:8000/auth/github/callback
GITHUB_OAUTH_SCOPE=read:user user:email
GITHUB_TOKEN_ENCRYPTION_KEY=replace-with-a-fernet-key

OAUTH_COOKIE_SECURE=false
DEEPSEEK_API_KEY=
```

## Current Remaining Work

The main remaining tasks are:

```text
1. Add human approval endpoint.
2. Connect frontend approval button.
3. Create GitHub issue after approval.
4. Save GitHub issue URL/status to MongoDB.
5. Add stronger end-to-end tests.
6. Prepare and publish the JavaScript SDK to npm.
7. Add Python SDK after JavaScript SDK is stable.
```

## Important Design Decisions

Raw logs are saved first, before AI processing.

AI processing is asynchronous so the sender receives a quick `202 Accepted`.

Analyzer nodes receive structured error data, not only the raw log.

The supervisor router selects which analyzer nodes should run, so every error does not need every analyzer.

The aggregator creates the final incident object used by the dashboard.

Human approval is stored separately from AI confidence. AI can recommend, but it should not automatically open GitHub issues.
