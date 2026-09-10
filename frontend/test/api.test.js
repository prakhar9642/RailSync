import { test } from "node:test";
import assert from "node:assert/strict";
import { optimizePlan, reoptimizePlan, getTerritories, ApiError } from "../src/services/api.js";
import { riskOptions } from "../src/utils/risk.js";

test("Planning sends the real optimize request and forwards its response", async () => {
  const original = globalThis.fetch;
  try {
    const returned = { status: "success", blocks: [{ block_id: "actual-result" }] };
    globalThis.fetch = async (url,options) => {
      assert.equal(url,"/api/optimize");
      assert.equal(options.method,"POST");
      assert.deepEqual(JSON.parse(options.body),{ territory_id: "fixture",risk_mode: "STATIC",risk_profiles: [] });
      return { ok: true,json: async () => returned };
    };
    assert.equal(await optimizePlan("fixture"),returned);
  } finally { globalThis.fetch = original; }
});

test("Territory discovery uses the shared backend registry endpoint", async () => {
  const original = globalThis.fetch;
  try {
    const returned = { territories: [{ territory_id: "public-demo" }] };
    globalThis.fetch = async (url, options) => {
      assert.equal(url, "/api/territories");
      assert.equal(options.method, undefined);
      return { ok: true, json: async () => returned };
    };
    assert.equal(await getTerritories(), returned);
  } finally { globalThis.fetch = original; }
});

test("Recovery sends immutable current plan, horizon and disruption to its own endpoint", async () => {
  const original = globalThis.fetch;
  const base = { blocks: [{ block_id:"B",tasks:["TASK"] }],unscheduled_tasks:["U"],
    planning_context: { territory_id:"fixture",horizon_start:"start",horizon_end:"end" } };
  const snapshot = structuredClone(base);
  const disruption = { type:"TRAIN_DELAY",train_id:"T",delay_minutes:25 };
  try {
    globalThis.fetch = async (url,options) => {
      assert.equal(url,"/api/reoptimize");
      assert.equal(options.method,"POST");
      const request = JSON.parse(options.body);
      assert.deepEqual(request.current_plan,{ blocks:base.blocks,unscheduled_tasks:base.unscheduled_tasks });
      assert.equal(request.horizon_start,"start");
      assert.deepEqual(request.disruption,disruption);
      return { ok:true,json:async () => ({ recovered_plan:{ blocks:[] } }) };
    };
    assert.deepEqual(await reoptimizePlan(base,disruption),{ recovered_plan:{ blocks:[] } });
    assert.deepEqual(base,snapshot);
  } finally { globalThis.fetch = original; }
});

test("Backend failure and abort never return fabricated plans", async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ ok:false,status:503,json:async () => ({ detail:{code:"NO_USABLE_PLAN",message:"No incumbent"} }) });
    await assert.rejects(optimizePlan("fixture"),(error) => error instanceof ApiError && error.code === "NO_USABLE_PLAN");
    globalThis.fetch = async () => { throw new TypeError("offline"); };
    await assert.rejects(optimizePlan("fixture"),/backend is unavailable/);
    globalThis.fetch = async () => { throw new DOMException("Aborted","AbortError"); };
    await assert.rejects(optimizePlan("fixture"),(error) => error.name === "AbortError");
  } finally { globalThis.fetch = original; }
});

test("Risk transfer requires explicit complete selection and is omitted in static mode", () => {
  assert.deepEqual(riskOptions({mode:"ML_ASSISTED"}),{risk_mode:"ML_ASSISTED",risk_profiles:[]});
  const selection={mode:"ML_ASSISTED",target:"T|S",profile:"12345|STATION"};
  assert.deepEqual(riskOptions(selection).risk_profiles,[{train_id:"T",section_id:"S",historical_train_id:"12345",historical_station_id:"STATION"}]);
  assert.deepEqual(riskOptions({...selection,mode:"STATIC"}).risk_profiles,[]);
});
