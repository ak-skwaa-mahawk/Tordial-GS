"use strict";

const fs = require("fs");
const crypto = require("crypto");

const path = "./tests/perf-summary.json";

if (!fs.existsSync(path)) {
  console.error("❌ No perf-summary.json found");
  process.exit(1);
}

try {
  const raw = fs.readFileSync(path, "utf8");
  const data = JSON.parse(raw);
  const { receipt, timestamp, compTime, decTime, ratio, threshold } = data;

  if (!receipt) {
    console.error("❌ Missing receipt field in perf-summary.json");
    process.exit(1);
  }

  const canonicalPayload = JSON.stringify({
    compTime,
    decTime,
    ratio,
    threshold,
    timestamp
  });

  const rehash = crypto.createHash("sha256").update(canonicalPayload).digest("hex");

  if (rehash === receipt) {
    console.log(`✅ Verified Fact Receipt: ${receipt}`);
    process.exit(0);
  } else {
    console.error("❌ Receipt mismatch");
    console.error(`   Expected: ${receipt}`);
    console.error(`   Computed: ${rehash}`);
    process.exit(2);
  }
} catch (err) {
  console.error(`❌ Verification error: ${err.message}`);
  process.exit(1);
}
