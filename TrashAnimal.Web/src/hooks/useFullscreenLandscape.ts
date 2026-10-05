import { useCallback, useEffect, useState } from 'react';

export function useFullscreenLandscape() {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [supportsFullscreen, setSupportsFullscreen] = useState(false);

  useEffect(() => {
    // Check browser support
    const supported =
      !!document.fullscreenEnabled &&
      ('orientation' in screen && 'lock' in screen.orientation);
    setSupportsFullscreen(supported);

    // Listen for fullscreen changes (ESC key, etc.)
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const enterFullscreen = useCallback(async () => {
    try {
      await document.documentElement.requestFullscreen();
      // Lock to landscape; ignore if orientation.lock fails (iOS often rejects)
      await screen.orientation.lock('landscape').catch(() => {});
      setIsFullscreen(true);
    } catch (error) {
      console.error('Fullscreen request failed:', error);
    }
  }, []);

  const exitFullscreen = useCallback(async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      }
      setIsFullscreen(false);
    } catch (error) {
      console.error('Exiting fullscreen failed:', error);
    }
  }, []);

  return { enterFullscreen, exitFullscreen, isFullscreen, supportsFullscreen };
}
