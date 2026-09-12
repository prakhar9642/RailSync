import { test } from "node:test";
import assert from "node:assert/strict";
import { optimizePlan, reoptimizePlan, getTerritories, ApiError } from "../src/services/api.js";
import {
  isPublicTerritory,
  findExactProfileMatches,
  effectiveRiskStatus,
  riskOptions,
} from "../src/utils/risk.js";

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
      assert.equal(url, "/api/territories?include_test=false");
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

test("Synthetic fixture: incomplete binding is Off, complete explicit binding is Experimental", () => {
  const fixture = { territory_id: "eastern_hdn_test_fixture" };
  assert.equal(effectiveRiskStatus({ mode: "STATIC" }, fixture), "Off");
  assert.equal(effectiveRiskStatus({ mode: "ML_ASSISTED", target: "", profile: "" }, fixture), "Off");
  assert.equal(effectiveRiskStatus({ mode: "ML_ASSISTED", target: "TR101|SEC_A", profile: "" }, fixture), "Off");
  assert.equal(effectiveRiskStatus({ mode: "ML_ASSISTED", target: "", profile: "12345|STN" }, fixture), "Off");
  assert.equal(
    effectiveRiskStatus({ mode: "ML_ASSISTED", target: "TR101|SEC_A", profile: "12345|STN" }, fixture),
    "Experimental"
  );
});

test("Public territory: evaluates to Unavailable when no exact profile match exists", () => {
  const publicTerritory = {
    territory_id: "saktigarh_memari_public_demo",
    provenance: [{ label: "PUBLIC_TIMETABLE_DERIVED" }],
  };
  assert.equal(isPublicTerritory(publicTerritory), true);
  assert.equal(effectiveRiskStatus({ mode: "STATIC" }, publicTerritory, []), "Unavailable");
  assert.equal(
    effectiveRiskStatus(
      { mode: "ML_ASSISTED", target: "37814|SEC_1", profile: "12345|BWN" },
      publicTerritory,
      []
    ),
    "Unavailable"
  );
  assert.deepEqual(
    riskOptions({ mode: "ML_ASSISTED", target: "37814|SEC_1", profile: "12345|BWN" }, publicTerritory),
    { risk_mode: "STATIC", risk_profiles: [] }
  );
});

test("Exact profile matching: strictly requires identical train_id without fuzzy or route/station matching", () => {
  const publicTrains = [
    { train_id: "37786" },
    { train_id: "37814" },
    { train_id: "37818" },
    { train_id: "37782" },
    { train_id: "37824" },
  ];

  // Disjoint profile IDs (simulating aggregate delay dataset which contains long-distance express trains)
  const unrelatedProfiles = [
    { train_id: "02501", station_code: "BWN", train_name: "AGTL SPECIAL" },
    { train_id: "12346", station_code: "BWN", train_name: "SARAIGHAT EXP" },
  ];
  assert.deepEqual(findExactProfileMatches(publicTrains, unrelatedProfiles), []);

  // No partial or fuzzy matches
  const partialProfiles = [
    { train_id: "3781", station_code: "BWN" },
    { train_id: "378140", station_code: "BWN" },
    { train_id: "EMU-37814", station_code: "BWN" },
  ];
  assert.deepEqual(findExactProfileMatches(publicTrains, partialProfiles), []);

  // Genuine exact match
  const matchedProfile = { train_id: "37814", station_code: "BWN", train_name: "HOWRAH LOCAL" };
  const matches = findExactProfileMatches(publicTrains, [...unrelatedProfiles, matchedProfile]);
  assert.deepEqual(matches, [matchedProfile]);

  // When exact match is available on public territory
  const publicTerritory = { territory_id: "saktigarh_memari_public_demo" };
  assert.equal(effectiveRiskStatus({ mode: "STATIC" }, publicTerritory, matches), "Off");
  assert.equal(
    effectiveRiskStatus({ mode: "ML_ASSISTED", target: "", profile: "" }, publicTerritory, matches),
    "Off"
  );
  assert.equal(
    effectiveRiskStatus(
      { mode: "ML_ASSISTED", target: "37814|SEC_1", profile: "37814|BWN" },
      publicTerritory,
      matches
    ),
    "Experimental"
  );
});
