import { useFullscreenLandscape } from '../../hooks/useFullscreenLandscape';
import { useIsPhoneLandscape, useIsTabletLandscape } from '../../hooks/useLandscapeBreakpoint';

/** Enter/exit fullscreen+landscape-lock toggle for the game board, positioned immediately to the
 * left of `GameBoardThemeToggle` in the top-right corner. Only meaningful on touch landscape
 * devices — `useFullscreenLandscape`'s orientation lock and `PortraitOverlay`'s "Enter Fullscreen
 * Landscape" prompt are already scoped the same way, so desktop mouse users never see this. */
function FullscreenToggleButton() {
  const { enterFullscreen, exitFullscreen, isFullscreen, supportsFullscreen } = useFullscreenLandscape();
  const isPhoneLandscape = useIsPhoneLandscape();
  const isTabletLandscape = useIsTabletLandscape();

  if (!supportsFullscreen || !(isPhoneLandscape || isTabletLandscape)) {
    return null;
  }

  return (
    <button
      type="button"
      onClick={() => (isFullscreen ? exitFullscreen() : enterFullscreen())}
      aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
      className="gb-glass fixed right-[92px] top-6 z-20 flex h-[60px] w-[60px] items-center justify-center rounded-full"
    >
      <svg
        width="26"
        height="26"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--gb-text-primary)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {isFullscreen ? (
          <>
            <path d="M9 3v4a2 2 0 0 1-2 2H3" />
            <path d="M21 9h-4a2 2 0 0 1-2-2V3" />
            <path d="M3 15h4a2 2 0 0 1 2 2v4" />
            <path d="M15 21v-4a2 2 0 0 1 2-2h4" />
          </>
        ) : (
          <>
            <path d="M3 9V5a2 2 0 0 1 2-2h4" />
            <path d="M21 9V5a2 2 0 0 0-2-2h-4" />
            <path d="M3 15v4a2 2 0 0 0 2 2h4" />
            <path d="M21 15v4a2 2 0 0 1-2 2h-4" />
          </>
        )}
      </svg>
    </button>
  );
}

export default FullscreenToggleButton;
