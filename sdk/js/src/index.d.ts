export interface ErrorLogClientOptions {
  apiKey: string;
  endpoint?: string;
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
  fetchImpl?: typeof fetch;
  throwOnFailure?: boolean;
}

export interface CaptureOptions {
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
  headers?: Record<string, string>;
  source?: string;
}

export interface ErrorLogSuccessResult {
  ok: true;
  status: string;
  errorId?: string;
  httpStatus: number;
  response: Record<string, unknown>;
}

export interface ErrorLogFailureResult {
  ok: false;
  status: "failed";
  error: string;
}

export type ErrorLogResult = ErrorLogSuccessResult | ErrorLogFailureResult;

export class ErrorLogClient {
  constructor(options: ErrorLogClientOptions);

  capture(rawLog: unknown, options?: CaptureOptions): Promise<ErrorLogResult>;

  captureException(error: unknown, options?: CaptureOptions): Promise<ErrorLogResult>;

  captureAndForget(rawLog: unknown, options?: CaptureOptions): void;

  captureExceptionAndForget(error: unknown, options?: CaptureOptions): void;

  installGlobalHandlers(options?: CaptureOptions): () => void;

  flush(): Promise<void>;

  shutdown(): void;
}

export function createClient(options: ErrorLogClientOptions): ErrorLogClient;

export function formatException(error: unknown): string;

export default ErrorLogClient;
