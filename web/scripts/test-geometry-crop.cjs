const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const outDir = path.join(__dirname, ".geometry-crop-test");
const tsc = path.join(root, "node_modules", "typescript", "bin", "tsc");

fs.rmSync(outDir, { recursive: true, force: true });

try {
  execFileSync(
    process.execPath,
    [
      tsc,
      "--target",
      "ES2022",
      "--module",
      "ES2022",
      "--moduleResolution",
      "node",
      "--rootDir",
      ".",
      "--outDir",
      outDir,
      "--skipLibCheck",
      "--strict",
      "scripts/geometry-crop.test.ts",
      "src/utils/geometryCrop.ts",
    ],
    { cwd: root, stdio: "inherit" },
  );
  execFileSync(process.execPath, [path.join(outDir, "scripts", "geometry-crop.test.js")], {
    cwd: root,
    stdio: "inherit",
  });
} finally {
  fs.rmSync(outDir, { recursive: true, force: true });
}
