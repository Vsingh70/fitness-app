// No "use client" directive: this hook is imported only by client components
// (which carry the boundary), so it doesn't need its own — and adding one would
// count against the client-component budget for no benefit.
import { useEffect, useState } from "react";

/**
 * Returns `value` only after it has stopped changing for `delayMs`. Use for
 * inputs that trigger network requests (search-as-you-type) so we fire one
 * request for the settled query instead of one per keystroke.
 */
export function useDebouncedValue<T>(value: T, delayMs = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
