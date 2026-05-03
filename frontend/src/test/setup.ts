import "@testing-library/jest-dom/vitest";

class NoopResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// @ts-ignore -- assigning to global; types vary across DOM/Node lib versions
globalThis.ResizeObserver = globalThis.ResizeObserver ?? NoopResizeObserver;
