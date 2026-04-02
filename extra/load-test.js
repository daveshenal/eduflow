import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const jobsStarted = new Counter("jobs_started");
const errorRate = new Rate("error_rate");
const responseTime = new Trend("response_time");

// ─── Student plan: kept very light ───────────────────────────────────────────
// Max 20 VUs, total test ~10 minutes, estimated Azure cost < $0.05
// Still tests: replica scaling, cold-start latency, scale-in task kill risk
// ─────────────────────────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    // Scenario 1: Gentle ramp — verifies ACA scales at least 1 extra replica
    gradual_ramp: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "2m", target: 5 }, // Warm up
        { duration: "3m", target: 15 }, // Trigger scale rule (HTTP threshold=10)
        { duration: "2m", target: 20 }, // Light stress
        { duration: "1m", target: 0 }, // Scale-in: watch for lost bg tasks
      ],
      gracefulRampDown: "30s",
      tags: { scenario: "gradual" },
    },

    // Scenario 2: Small spike — tests cold-start behaviour
    spike: {
      executor: "ramping-vus",
      startTime: "9m", // Runs after gradual_ramp finishes
      startVUs: 0,
      stages: [
        { duration: "15s", target: 20 }, // Quick ramp
        { duration: "45s", target: 20 }, // Hold briefly
        { duration: "15s", target: 0 }, // Drop off
      ],
      tags: { scenario: "spike" },
    },
  },

  thresholds: {
    // Fire-and-forget endpoint — should always respond fast
    "http_req_duration{scenario:gradual}": ["p(95)<500"],
    "http_req_duration{scenario:spike}": ["p(95)<1000"], // Extra slack for cold-start
    http_req_failed: ["rate<0.05"], // Under 5% errors
    error_rate: ["rate<0.05"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const CALLBACK_URL = __ENV.CALLBACK_URL || "";

function buildPayload(vu = 0, iter = 0) {
  return JSON.stringify({
    job_id: `job-${vu}-${iter}-${Date.now()}`,
    index_id: `idx-${Math.floor(Math.random() * 9999)}`,
    learning_focus: "assessment",
    topic: "Readmission prevention",
    target_audience: "nurses",
    duration: 10,
    num_docs: 2,
    voice: "alloy",
    callback_url: CALLBACK_URL,
  });
}

export default function () {
  const res = http.post(
    `${BASE_URL}/gen/start-test`,
    buildPayload(__VU, __ITER),
    {
      headers: { "Content-Type": "application/json" },
      timeout: "10s",
      tags: { name: "start_job" },
    },
  );

  responseTime.add(res.timings.duration);

  const ok = check(res, {
    "status 200": (r) => r.status === 200,
    "body has started": (r) => r.json("status") === "started",
    "response under 500ms": (r) => r.timings.duration < 500,
  });

  errorRate.add(!ok);
  if (ok) jobsStarted.add(1);

  sleep(0.5); // Small pause — keeps load gentle on student plan
}

export function setup() {
  const res = http.post(`${BASE_URL}/gen/start-test`, buildPayload(0, 0), {
    headers: { "Content-Type": "application/json" },
  });
  if (res.status !== 200) {
    throw new Error(`Server not ready. Got HTTP ${res.status}: ${res.body}`);
  }
  console.log("✅ Server reachable. Starting light load test...");
  console.log("👀 Watch in Azure Portal → your Container App → Metrics:");
  console.log("   - Replica Count");
  console.log("   - Memory Working Set");
  console.log("   - Request Count");
}

export function teardown() {
  console.log("");
  console.log("✅ Test complete. Check Azure Portal for:");
  console.log("   Replica count     → did it scale beyond 1?");
  console.log("   Memory per replica → rising = bg tasks accumulating");
  console.log(
    "   HTTP 5xx errors   → spike during scale-in = jobs were killed",
  );
}
