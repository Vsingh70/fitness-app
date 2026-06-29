import "@testing-library/jest-dom/vitest";

// jsdom reports every element's layout box as 0×0. `@tanstack/react-virtual`
// reads the scroll container's `offsetHeight` (via `getRect`) to size its
// window, and when that height is 0 it renders ZERO rows (`calculateRange`
// bails on a zero viewport). Give the virtualizer a stable, non-zero viewport
// so virtualized lists mount a bounded window under test instead of nothing.
// Without this, any component that windows its rows would render empty in
// jsdom. See tests/perf/virtualization.test.tsx for the boundedness guard.
const VIEWPORT_PX = 600;

Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
  configurable: true,
  get() {
    return VIEWPORT_PX;
  },
});
Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
  configurable: true,
  get() {
    return VIEWPORT_PX;
  },
});

const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
Element.prototype.getBoundingClientRect = function getBoundingClientRect(): DOMRect {
  const rect = originalGetBoundingClientRect.call(this) as DOMRect;
  return {
    ...rect,
    width: rect.width || VIEWPORT_PX,
    height: rect.height || VIEWPORT_PX,
    bottom: rect.bottom || VIEWPORT_PX,
    right: rect.right || VIEWPORT_PX,
    toJSON: rect.toJSON,
  } as DOMRect;
};

// jsdom lacks the Pointer Capture API; `vaul` (the drawer behind <Sheet>) calls
// setPointerCapture on pointer-down and throws "not a function" otherwise, which
// surfaces as an unhandled error and fails the run even when assertions pass.
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
  Element.prototype.hasPointerCapture = () => false;
}
// Radix/vaul also call scrollIntoView, which jsdom doesn't implement.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
