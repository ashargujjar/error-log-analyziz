export const initialIncidents = [
  {
    id: "INC-2026-1042",
    title: "Payment API 500 spike",
    service: "payments-api",
    severity: "Critical",
    status: "Awaiting approval",
    detectedAt: "2026-10-04 09:18",
    environment: "production",
    confidence: 96,
    owner: "Platform Reliability",
    gitHubIssue: null,
    summary:
      "The model detected a sharp increase in HTTP 500 responses after a deploy. It recommends opening a GitHub issue for rollback validation and database connection pool review.",
    signal:
      "Error rate increased from 0.4% to 8.7% across checkout requests. Logs show repeated Prisma timeout errors in the payment authorization path.",
    impact: "Checkout failures may affect live customer transactions.",
    recommendation:
      "Approve GitHub issue creation, assign the payments-api owner, and include the generated log summary with the suspected release window.",
    timeline: [
      "09:12 - Deploy 88f2c19 completed",
      "09:15 - Error budget burn alert triggered",
      "09:18 - AI triage grouped 413 related errors",
      "09:21 - Human approval requested",
    ],
    logs: [
      "ERROR prisma: Timed out fetching a new connection from the connection pool",
      "POST /api/checkout/authorize returned 500 in 4187ms",
      "CorrelationId=pay_8K21 route=/checkout/authorize region=us-east-1",
    ],
  },
  {
    id: "INC-2026-1038",
    title: "Queue worker retry storm",
    service: "notification-worker",
    severity: "High",
    status: "Awaiting approval",
    detectedAt: "2026-10-04 08:44",
    environment: "production",
    confidence: 91,
    owner: "Messaging",
    gitHubIssue: null,
    summary:
      "Retry volume has exceeded baseline after downstream provider throttling. The AI grouped related exceptions and prepared a GitHub issue for human approval.",
    signal:
      "The notification queue depth grew 5x while provider calls returned repeated 429 responses.",
    impact: "Customer emails and SMS notifications may be delayed.",
    recommendation:
      "Open an issue to track rate-limit handling, add exponential backoff, and review dead-letter queue thresholds.",
    timeline: [
      "08:32 - Provider throttling begins",
      "08:39 - Queue depth crosses warning threshold",
      "08:44 - AI triage detects retry storm",
      "08:47 - Approval request generated",
    ],
    logs: [
      "WARN provider.send failed with 429 Too Many Requests",
      "RetryAttempt=7 messageType=receipt-email",
      "QueueDepth notification-primary reached 12843 messages",
    ],
  },
  {
    id: "INC-2026-1027",
    title: "Auth token validation failures",
    service: "identity-gateway",
    severity: "Medium",
    status: "Issue opened",
    detectedAt: "2026-10-03 18:12",
    environment: "staging",
    confidence: 86,
    owner: "Identity",
    gitHubIssue: "GH-8421",
    summary:
      "A staging certificate rotation caused token validation failures. A GitHub issue was opened and assigned to Identity.",
    signal:
      "JWT signature validation failed for staging clients using the rotated certificate chain.",
    impact: "Internal staging testing blocked for OAuth callback flows.",
    recommendation:
      "Review the certificate rotation checklist and update staging trust bundle automation.",
    timeline: [
      "18:05 - Certificate rotation job completed",
      "18:09 - Auth validation errors begin",
      "18:12 - AI incident created",
      "18:16 - GitHub issue GH-8421 opened",
    ],
    logs: [
      "ERROR jwt.verify failed: unable to get local issuer certificate",
      "GET /oauth/callback returned 401 in 92ms",
      "Client=staging-dashboard issuer=identity-gateway",
    ],
  },
  {
    id: "INC-2026-1019",
    title: "Search index lag",
    service: "catalog-search",
    severity: "Low",
    status: "Resolved",
    detectedAt: "2026-10-02 14:36",
    environment: "production",
    confidence: 78,
    owner: "Commerce",
    gitHubIssue: "GH-8398",
    summary:
      "Catalog search indexing lag briefly exceeded the service objective and recovered after worker scaling.",
    signal:
      "Index freshness lag reached 21 minutes before autoscaling added two workers.",
    impact: "New product updates appeared late in search results.",
    recommendation:
      "Keep the historical incident for trend analysis and evaluate worker scale-up thresholds.",
    timeline: [
      "14:22 - Index lag crosses warning level",
      "14:36 - AI incident created",
      "14:43 - Worker pool scaled",
      "15:04 - Lag returned to normal",
    ],
    logs: [
      "INFO indexLagSeconds=1260 shard=catalog-products-3",
      "WARN bulkIndex queue high watermark reached",
      "INFO worker scale-out completed desired=8 active=8",
    ],
  },
];
