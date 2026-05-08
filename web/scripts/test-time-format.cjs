const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const sourcePath = path.join(__dirname, "..", "src", "utils", "time.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const sandbox = { exports: {}, Intl, Date, Number, Object };
vm.runInNewContext(compiled.outputText, sandbox, { filename: sourcePath });

assert.equal(
  sandbox.exports.formatServiceDateTime("2026-05-07T17:56:57.995604Z"),
  "2026/05/08 01:56",
);
assert.equal(
  sandbox.exports.formatServiceTime("2026-05-07T17:56:57.995604Z"),
  "01:56:57",
);
assert.equal(sandbox.exports.formatServiceTime(null), "—");
assert.equal(sandbox.exports.formatServiceDateTime("not-a-date"), "not-a-date");
