// Typed accessor for the shared performance budgets. Single source of truth lives
// in perf/budgets.json so the Vitest, bundle, and Playwright layers all agree.
import budgets from "../../perf/budgets.json";

export default budgets;
export const STATIC = budgets.static;
export const RENDER = budgets.render;
export const BUNDLE = budgets.bundleKBGzip;
export const WEB_VITALS = budgets.webVitals;
export const ROUTES_TO_PROBE = budgets.routesToProbe;
