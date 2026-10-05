import DayNightBackground from '../../components/gameboard/DayNightBackground';
import GameBoardThemeToggle from '../../components/gameboard/GameBoardThemeToggle';
import FullscreenToggleButton from '../../components/gameboard/FullscreenToggleButton';
import GameLogButton from '../../components/gameboard/GameLogButton';

/** Renders just the game board's fixed-position "chrome" (background + top-right button cluster)
 * without a real game session, for checking button sizing/positioning/theme-icon-resolution in
 * isolation. */
function BoardChromePreview() {
  return (
    <div className="gb-root">
      <DayNightBackground />
      <FullscreenToggleButton />
      <GameBoardThemeToggle />
      <GameLogButton onClick={() => {}} />
    </div>
  );
}

export default BoardChromePreview;
