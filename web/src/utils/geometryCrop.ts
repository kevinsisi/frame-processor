export type Frame = { left: number; top: number; width: number; height: number };

export const MIN_CROP_ZOOM = 1;
export const MAX_CROP_ZOOM = 3;
export const CROP_HANDLES = ["n", "e", "s", "w", "ne", "se", "sw", "nw"] as const;

export type CropHandle = (typeof CROP_HANDLES)[number];

export type CropParams = {
  crop_zoom: number;
  crop_x: number;
  crop_y: number;
};

export function containedImageFrame(
  shell: { width: number; height: number },
  image: { width: number; height: number },
): Frame {
  const shellRatio = shell.width / shell.height;
  const imageRatio = image.width / image.height;
  if (imageRatio > shellRatio) {
    const height = shell.width / imageRatio;
    return { left: 0, top: (shell.height - height) / 2, width: shell.width, height };
  }
  const width = shell.height * imageRatio;
  return { left: (shell.width - width) / 2, top: 0, width, height: shell.height };
}

export function cropFrame(zoom: number, x: number, y: number, imageFrame: Frame): Frame {
  const safeZoom = clamp(zoom, MIN_CROP_ZOOM, MAX_CROP_ZOOM);
  const width = imageFrame.width / safeZoom;
  const height = imageFrame.height / safeZoom;
  const maxLeft = Math.max(0, imageFrame.width - width);
  const maxTop = Math.max(0, imageFrame.height - height);
  const left = maxLeft / 2 + (clamp(x, -100, 100) / 100) * (maxLeft / 2);
  const top = maxTop / 2 + (clamp(y, -100, 100) / 100) * (maxTop / 2);
  return {
    left: imageFrame.left + clamp(left, 0, maxLeft),
    top: imageFrame.top + clamp(top, 0, maxTop),
    width,
    height,
  };
}

export function moveCropFrame(crop: Frame, imageFrame: Frame, dx: number, dy: number): Frame {
  return {
    ...crop,
    left: clamp(crop.left + dx, imageFrame.left, imageFrame.left + imageFrame.width - crop.width),
    top: clamp(crop.top + dy, imageFrame.top, imageFrame.top + imageFrame.height - crop.height),
  };
}

export function resizeCropFrame(
  crop: Frame,
  imageFrame: Frame,
  handle: CropHandle,
  pointerX: number,
  pointerY: number,
): Frame {
  const imageRight = imageFrame.left + imageFrame.width;
  const imageBottom = imageFrame.top + imageFrame.height;
  const cropRight = crop.left + crop.width;
  const cropBottom = crop.top + crop.height;
  const cropCenterX = crop.left + crop.width / 2;
  const cropCenterY = crop.top + crop.height / 2;
  const aspect = imageFrame.width / imageFrame.height;
  const minWidth = imageFrame.width / MAX_CROP_ZOOM;
  const maxWidthByX = handle.includes("e")
    ? imageRight - crop.left
    : handle.includes("w")
      ? cropRight - imageFrame.left
      : Math.min(cropCenterX - imageFrame.left, imageRight - cropCenterX) * 2;
  const maxWidthByY = handle.includes("s")
    ? (imageBottom - crop.top) * aspect
    : handle.includes("n")
      ? (cropBottom - imageFrame.top) * aspect
      : Math.min(cropCenterY - imageFrame.top, imageBottom - cropCenterY) * 2 * aspect;
  const maxWidth = Math.max(minWidth, Math.min(imageFrame.width, maxWidthByX, maxWidthByY));
  const candidates: number[] = [];
  if (handle.includes("e")) candidates.push(crop.width + pointerX - cropRight);
  if (handle.includes("w")) candidates.push(crop.width + crop.left - pointerX);
  if (handle.includes("s")) candidates.push((crop.height + pointerY - cropBottom) * aspect);
  if (handle.includes("n")) candidates.push((crop.height + crop.top - pointerY) * aspect);

  const width = clamp(candidates.length ? Math.min(...candidates) : crop.width, minWidth, maxWidth);
  const height = width / aspect;
  const left = handle.includes("w")
    ? cropRight - width
    : handle.includes("e")
      ? crop.left
      : cropCenterX - width / 2;
  const top = handle.includes("n")
    ? cropBottom - height
    : handle.includes("s")
      ? crop.top
      : cropCenterY - height / 2;

  return {
    left: clamp(left, imageFrame.left, imageRight - width),
    top: clamp(top, imageFrame.top, imageBottom - height),
    width,
    height,
  };
}

export function applyCropFrame<T extends CropParams>(params: T, crop: Frame, imageFrame: Frame): T {
  const zoom = clamp(imageFrame.width / crop.width, MIN_CROP_ZOOM, MAX_CROP_ZOOM);
  const width = imageFrame.width / zoom;
  const height = imageFrame.height / zoom;
  const maxLeft = Math.max(0, imageFrame.width - width);
  const maxTop = Math.max(0, imageFrame.height - height);
  const left = clamp(crop.left - imageFrame.left, 0, maxLeft);
  const top = clamp(crop.top - imageFrame.top, 0, maxTop);
  const cropX = maxLeft > 0 ? ((left - maxLeft / 2) / (maxLeft / 2)) * 100 : 0;
  const cropY = maxTop > 0 ? ((top - maxTop / 2) / (maxTop / 2)) * 100 : 0;
  return {
    ...params,
    crop_zoom: roundNumber(zoom, 2),
    crop_x: roundNumber(clamp(cropX, -100, 100), 1),
    crop_y: roundNumber(clamp(cropY, -100, 100), 1),
  };
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function roundNumber(value: number, decimals: number): number {
  const scale = 10 ** decimals;
  return Math.round(value * scale) / scale;
}
