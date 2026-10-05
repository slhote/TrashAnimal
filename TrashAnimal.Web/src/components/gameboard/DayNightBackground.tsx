import { useEffect, useState } from 'react';
import { useIsDarkResolved } from '../../hooks/useIsDarkResolved';
import { DAY_BACKGROUND_IMAGE, NIGHT_BACKGROUND_IMAGE } from '../../pages/GameBoard/assetMaps';

// On first render, only fetch the background matching the current theme.
// The other variant loads lazily on first theme change, preserving crossfade for every toggle after that.
// First toggle in a session won't have the incoming image preloaded, so it pops in rather than crossfading instantly — an accepted, strictly-better-than-today trade-off.
function DayNightBackground() {
  const isNight = useIsDarkResolved();
  const [hasSeenDay, setHasSeenDay] = useState(!isNight);
  const [hasSeenNight, setHasSeenNight] = useState(isNight);

  useEffect(() => {
    if (isNight) setHasSeenNight(true);
    else setHasSeenDay(true);
  }, [isNight]);

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      {hasSeenDay && (
        <img
          src={DAY_BACKGROUND_IMAGE}
          alt=""
          fetchPriority="high"
          className="absolute inset-0 h-full w-full object-cover transition-opacity duration-[600ms]"
          style={{ opacity: isNight ? 0 : 1 }}
        />
      )}
      {hasSeenNight && (
        <img
          src={NIGHT_BACKGROUND_IMAGE}
          alt=""
          fetchPriority="high"
          className="absolute inset-0 h-full w-full object-cover transition-opacity duration-[600ms]"
          style={{ opacity: isNight ? 1 : 0 }}
        />
      )}
      <div
        className="absolute inset-0 transition-colors duration-[600ms]"
        style={{ background: isNight ? 'rgba(5,10,30,.4)' : 'rgba(10,20,40,.08)' }}
      />
    </div>
  );
}

export default DayNightBackground;
