import { useTheme } from '../../hooks/useTheme';
import { useIsDarkResolved } from '../../hooks/useIsDarkResolved';

/** Sun/moon toggle for the game board, cycling only light/dark (no 'system' step here — the
 * board needs an explicit day/night state to show, unlike the site-wide ThemeToggle). */
function GameBoardThemeToggle() {
  const { setTheme } = useTheme();
  const isDark = useIsDarkResolved();

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label={isDark ? 'Switch to day' : 'Switch to night'}
      className="gb-glass fixed right-6 top-6 z-20 flex h-[60px] w-[60px] items-center justify-center rounded-full"
    >
      <span
        className="h-[26px] w-[26px] rounded-full transition-all duration-[400ms]"
        style={
          isDark
            ? { background: '#e8eef7', boxShadow: 'inset 8px -4px 0 3px #0a1020' }
            : {
                background: 'radial-gradient(circle, #ffe27a, #f2b134)',
                boxShadow: '0 0 14px 4px rgba(255,210,90,.7)',
              }
        }
      />
    </button>
  );
}

export default GameBoardThemeToggle;
