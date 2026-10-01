// k6 smoke/load test (free, open source): https://k6.io
//
//   docker run --rm -i --network host -e BASE=http://localhost:8000 grafana/k6 run - < tests/load/smoke.js
//   make load
//
// Simulates the realistic mix: analysts and committee members reading case lists and case detail
// (most traffic), product owners creating cases and running intake (the expensive path).
// Run against LLM_MODE=offline or replay so the load test never burns free-tier quota.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE || "http://localhost:8000";

export const options = {
  scenarios: {
    readers: { executor: "constant-vus", vus: 20, duration: "60s", exec: "reader" },
    intake: { executor: "constant-arrival-rate", rate: 1, timeUnit: "2s", duration: "60s", preAllocatedVUs: 5, exec: "intake" },
  },
  thresholds: {
    "http_req_failed": ["rate<0.01"],
    "http_req_duration{kind:read}": ["p(95)<500"],
    "http_req_duration{kind:write}": ["p(95)<2000"],
    "checks": ["rate>0.99"],
  },
};

function login(username) {
  const r = http.post(`${BASE}/api/auth/login`, JSON.stringify({ username, password: "demo" }), {
    headers: { "Content-Type": "application/json" },
    tags: { kind: "write" },
  });
  check(r, { "login 200": (x) => x.status === 200 });
  return { headers: { Authorization: `Bearer ${r.json("token")}`, "Content-Type": "application/json" } };
}

export function setup() {
  return { analyst: login("arjun"), po: login("priya") };
}

export function reader(auth) {
  const list = http.get(`${BASE}/api/cases`, { ...auth.analyst, tags: { kind: "read" } });
  check(list, { "list 200": (x) => x.status === 200 });
  const cases = list.json();
  if (cases.length) {
    const c = cases[Math.floor(Math.random() * cases.length)];
    const d = http.get(`${BASE}/api/cases/${c.id}`, { ...auth.analyst, tags: { kind: "read" } });
    check(d, { "detail 200": (x) => x.status === 200 });
  }
  sleep(1);
}

export function intake(auth) {
  const body = {
    title: `Load test product ${__VU}-${__ITER}`,
    description: "Synthetic load-test change request for the smoke test.",
    change_type: "new_product",
    business_line: "Payments",
    document_text:
      "Retail customers in Avalon use the mobile app. Payments settle instantly. Expected monthly value is USD 3 million. " +
      "Controls: eKYC with liveness check, real-time sanctions screening.",
  };
  const c = http.post(`${BASE}/api/cases`, JSON.stringify(body), { ...auth.po, tags: { kind: "write" } });
  check(c, { "create 201": (x) => x.status === 201 });
  const x = http.post(`${BASE}/api/cases/${c.json("id")}/extract`, null, { ...auth.po, tags: { kind: "write" } });
  check(x, { "extract 200": (r) => r.status === 200 });
}
