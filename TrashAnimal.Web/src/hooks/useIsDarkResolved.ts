import { useEffect, useState } from 'react';
import { useTheme } from './useTheme';

/** Resolves 'system' against the OS media query so day/night can be a plain boolean. */
export function useIsDarkResolved(): boolean {
  const { theme } = useTheme();
  const [systemPrefersDark, setSystemPrefersDark] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches,
  );

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches);
    query.addEventListener('change', listener);
    return () => query.removeEventListener('change', listener);
  }, []);

  return theme === 'dark' || (theme === 'system' && systemPrefersDark);
}
