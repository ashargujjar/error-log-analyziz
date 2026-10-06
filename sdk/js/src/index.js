const DEFAULT_TIMEOUT_MS = 5000;
const DEFAULT_RETRIES = 2;
const DEFAULT_RETRY_DELAY_MS = 500;
const SDK_VERSION = "0.1.0";

export class ErrorLogClient {
  constructor(options = {}) {
    const {
      apiKey,
      endpoint = "http://127.0.0.1:8000/errors",
      timeoutMs = DEFAULT_TIMEOUT_MS,
      retries = DEFAULT_RETRIES,
      retryDelayMs = DEFAULT_RETRY_DELAY_MS,
      fetchImpl = globalThis.fetch,
      throwOnFailure = false,
    } = options;

    if (!apiKey) {
      throw new Error("ErrorLogClient requires an apiKey.");
    }

    if (!endpoint) {
      throw new Error("ErrorLogClient requires an endpoint.");
    }

    if (typeof fetchImpl !== "function") {
      throw new Error(
        "ErrorLogClient requires fetch. Use Node.js 18+ or pass fetchImpl.",
      );
    }

    this.apiKey = apiKey;
    this.endpoint = endpoint;
    this.timeoutMs = timeoutMs;
    this.retries = retries;
    this.retryDelayMs = retryDelayMs;
    this.fetchImpl = fetchImpl;
    this.throwOnFailure = throwOnFailure;
    this.closed = false;
  }

  async capture(rawLog, options = {}) {
    if (this.closed) {
      return this._failure("SDK client is already shut down.");
    }

    const body = this._normalizeRawLog(rawLog);
    if (!body.trim()) {
      return this._failure("Raw error log cannot be empty.");
    }

    return this._send(body, options);
  }

  async captureException(error, options = {}) {
    return this.capture(formatException(error), options);
  }

  captureAndForget(rawLog, options = {}) {
    this.capture(rawLog, options).catch(() => undefined);
  }

  captureExceptionAndForget(error, options = {}) {
    this.captureException(error, options).catch(() => undefined);
  }

  installGlobalHandlers(options = {}) {
    if (typeof process === "undefined" || typeof process.on !== "function") {
      return () => undefined;
    }

    const uncaughtHandler = (error) => {
      this.captureExceptionAndForget(error, {
        ...options,
        source: "uncaughtException",
      });
    };
    const rejectionHandler = (reason) => {
      this.captureExceptionAndForget(reason, {
        ...options,
        source: "unhandledRejection",
      });
    };

    process.on("uncaughtException", uncaughtHandler);
    process.on("unhandledRejection", rejectionHandler);

    return () => {
      process.off("uncaughtException", uncaughtHandler);
      process.off("unhandledRejection", rejectionHandler);
    };
  }

  async flush() {
    return undefined;
  }

  shutdown() {
    this.closed = true;
  }

  async _send(body, options) {
    const maxAttempts = Math.max(1, (options.retries ?? this.retries) + 1);
    let lastError;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        const response = await this._post(body, options);

        if (response.ok) {
          const data = await response.json().catch(() => ({}));
          return {
            ok: true,
            status: data.status || "pending",
            errorId: data.error_id,
            httpStatus: response.status,
            response: data,
          };
        }

        const message = await response.text().catch(() => "");
        lastError = new Error(
          `Error log request failed with HTTP ${response.status}${message ? `: ${message}` : ""}`,
        );

        if (!shouldRetryStatus(response.status) || attempt === maxAttempts) {
          break;
        }
      } catch (error) {
        lastError = error;
        if (attempt === maxAttempts) {
          break;
        }
      }

      await sleep(backoffDelay(options.retryDelayMs ?? this.retryDelayMs, attempt));
    }

    return this._failure(lastError?.message || "Error log request failed.");
  }

  async _post(body, options) {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      options.timeoutMs ?? this.timeoutMs,
    );

    try {
      return await this.fetchImpl(this.endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "text/plain",
          "X-Error-Log-SDK": `js/${SDK_VERSION}`,
          ...options.headers,
        },
        body,
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeout);
    }
  }

  _normalizeRawLog(rawLog) {
    if (rawLog instanceof Error) {
      return formatException(rawLog);
    }

    if (typeof rawLog === "string") {
      return rawLog;
    }

    try {
      return JSON.stringify(rawLog, null, 2) ?? String(rawLog ?? "");
    } catch {
      return String(rawLog ?? "");
    }
  }

  _failure(message) {
    if (this.throwOnFailure) {
      throw new Error(message);
    }

    return {
      ok: false,
      status: "failed",
      error: message,
    };
  }
}

export function createClient(options) {
  return new ErrorLogClient(options);
}

export function formatException(error) {
  if (error instanceof Error) {
    return error.stack || `${error.name}: ${error.message}`;
  }

  if (typeof error === "string") {
    return error;
  }

  try {
    return JSON.stringify(error, null, 2) ?? String(error ?? "");
  } catch {
    return String(error ?? "");
  }
}

function shouldRetryStatus(status) {
  return status === 429 || status >= 500;
}

function backoffDelay(baseDelayMs, attempt) {
  return baseDelayMs * 2 ** Math.max(0, attempt - 1);
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export default ErrorLogClient;
