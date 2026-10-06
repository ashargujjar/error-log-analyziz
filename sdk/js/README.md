# Error Log Analyzer JavaScript SDK

Send raw server-side JavaScript error logs to the Error Log Analyzer backend.

The SDK sends the original raw log text to `POST /errors`. Your backend saves it as `pending`, processes it with the AI analyzer workflow, and shows the final incident in the dashboard.

## Install

```bash
npm install @error-log-analyzer/js-sdk
```

This package requires Node.js 18 or newer because it uses the built-in `fetch` API.

## Usage

```js
import { ErrorLogClient } from "@error-log-analyzer/js-sdk";

const client = new ErrorLogClient({
  apiKey: process.env.ERROR_LOG_API_KEY,
  endpoint: "http://127.0.0.1:8000/errors",
});

await client.capture("MongoDB connection refused at server startup");
```

The SDK sends:

```text
POST /errors
Authorization: Bearer <api_key>
Content-Type: text/plain
```

## Capture exceptions

```js
try {
  throw new Error("Database crashed");
} catch (error) {
  await client.captureException(error);
}
```

## Fire and forget

Use this when the error report should not block the request lifecycle:

```js
client.captureAndForget("background worker crashed");
client.captureExceptionAndForget(new Error("Queue failed"));
```

## Global Node.js handlers

```js
const removeHandlers = client.installGlobalHandlers();

// Later, if needed:
removeHandlers();
```

## Options

```js
const client = new ErrorLogClient({
  apiKey: process.env.ERROR_LOG_API_KEY,
  endpoint: "https://your-api.example.com/errors",
  timeoutMs: 5000,
  retries: 2,
  retryDelayMs: 500,
  throwOnFailure: false,
});
```

## Result

```js
const result = await client.capture("raw log");

if (result.ok) {
  console.log(result.errorId);
} else {
  console.error(result.error);
}
```

## Local checks

```bash
npm run check
npm test
npm pack --dry-run
```

## Publish

```bash
npm login
npm publish --access public
```

The scoped package name `@error-log-analyzer/js-sdk` requires access to the `error-log-analyzer` npm organization. If that organization does not exist in your npm account, rename the package before publishing.

Keep API keys on the server side. Do not expose this SDK key in browser React code.
