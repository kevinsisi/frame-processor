import {
  applyCropFrame,
  containedImageFrame,
  cropFrame,
  moveCropFrame,
  resizeCropFrame,
  type Frame,
} from "../src/utils/geometryCrop.js";

function assertClose(actual: number, expected: number, label: string): void {
  if (Math.abs(actual - expected) > 0.001) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

function assertFrame(actual: Frame, expected: Frame, label: string): void {
  assertClose(actual.left, expected.left, `${label}.left`);
  assertClose(actual.top, expected.top, `${label}.top`);
  assertClose(actual.width, expected.width, `${label}.width`);
  assertClose(actual.height, expected.height, `${label}.height`);
}

const shell = { width: 400, height: 300 };
const image = { width: 1600, height: 900 };
const imageFrame = containedImageFrame(shell, image);
assertFrame(imageFrame, { left: 0, top: 37.5, width: 400, height: 225 }, "containedImageFrame");

const centeredCrop = cropFrame(2, 0, 0, imageFrame);
assertFrame(centeredCrop, { left: 100, top: 93.75, width: 200, height: 112.5 }, "centeredCrop");

const movedCrop = moveCropFrame(centeredCrop, imageFrame, 400, -400);
assertFrame(movedCrop, { left: 200, top: 37.5, width: 200, height: 112.5 }, "move clamps to image bounds");

const seResize = resizeCropFrame(centeredCrop, imageFrame, "se", 350, 260);
assertFrame(seResize, { left: 100, top: 93.75, width: 250, height: 140.625 }, "resize se keeps aspect");

const westResize = resizeCropFrame(centeredCrop, imageFrame, "w", 120, 150);
assertFrame(westResize, { left: 120, top: 99.375, width: 180, height: 101.25 }, "resize west anchors right edge");

const params = applyCropFrame({ crop_zoom: 1, crop_x: 0, crop_y: 0 }, movedCrop, imageFrame);
assertClose(params.crop_zoom, 2, "applyCropFrame crop_zoom");
assertClose(params.crop_x, 100, "applyCropFrame crop_x");
assertClose(params.crop_y, -100, "applyCropFrame crop_y");
