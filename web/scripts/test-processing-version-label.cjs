const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const sourcePath = path.join(
  __dirname,
  "..",
  "src",
  "utils",
  "processingVersionLabel.ts",
);
const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const sandbox = { exports: {} };
vm.runInNewContext(compiled.outputText, sandbox, { filename: sourcePath });

const {
  presetLabel,
  denoiseLabel,
  cplLabel,
  chromaCleanLabel,
  detailPreserveLabel,
  formatAIVersionLabel,
  formatAIVersionFallbackLabel,
  formatBatchPresetLabel,
} = sandbox.exports;

assert.equal(presetLabel("showroom_white"), "展示間白");
assert.equal(presetLabel("outdoor_warm"), "戶外暖調");
assert.equal(presetLabel("night_cold"), "夜拍冷調");
assert.equal(presetLabel("unknown_preset"), "unknown_preset");

assert.equal(denoiseLabel("none"), "不降噪");
assert.equal(denoiseLabel("light"), "輕度降噪");
assert.equal(denoiseLabel("medium"), "中度降噪");
assert.equal(denoiseLabel("heavy"), "重度降噪");
assert.equal(denoiseLabel("ultra"), "ultra");

assert.equal(cplLabel("none"), "不做 CPL");
assert.equal(cplLabel("medium"), "CPL 中度");

assert.equal(chromaCleanLabel("none"), "不修正偽色");
assert.equal(chromaCleanLabel("high"), "偽色重度");

assert.equal(detailPreserveLabel("none"), "不保留細節");
assert.equal(detailPreserveLabel("low"), "細節輕度");

assert.equal(
  formatAIVersionLabel({
    version_number: 3,
    preset: "showroom_white",
    denoise_strength: "medium",
    chroma_clean_strength: "medium",
    detail_preserve_strength: "low",
    cpl_strength: "none",
  }),
  "AI v3：展示間白 / 中度降噪 / 偽色中度 / 細節輕度 / 不做 CPL",
);

// Unknown strength values pass through so future enum additions don't crash the UI.
assert.equal(
  formatAIVersionLabel({
    version_number: 7,
    preset: "experimental_warm",
    denoise_strength: "ultra",
    chroma_clean_strength: "off",
    detail_preserve_strength: "max",
    cpl_strength: "extreme",
  }),
  "AI v7：experimental_warm / ultra / off / max / extreme",
);

assert.equal(formatAIVersionFallbackLabel(5), "AI v5");
assert.equal(formatBatchPresetLabel("outdoor_warm"), "批次：戶外暖調");
assert.equal(formatBatchPresetLabel("unknown_preset"), "批次：unknown_preset");

console.log("processingVersionLabel: all assertions passed");
