import { ErrorLogClient } from "error-log-analyzer-js-sdk";

const client = new ErrorLogClient({
  apiKey: "ela_eTkIl3ftSRBSkcpRy_cnYRRqwzw8zH6B96EN9vL7kFU",
  endpoint: "http://127.0.0.1:8000/errors",
});

const result = await client.captureException(new Error("Test SDK error"));
console.log(result);
