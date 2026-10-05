import { lazy } from 'react';

/** Dev-only component previews, reachable at /dev-preview/:key (see DevPreviewPage). Add an entry
 * here whenever a component's visual states are worth checking in isolation — grouped card grids,
 * count badges, or anything else with boundary-count layout bugs (empty/single/full-row/full-grid)
 * that are easy to miss testing against one sample dataset. Each preview owns its own ?scenario=
 * values; keep them documented in a comment at the top of the preview file. */
export const DEV_PREVIEWS = {
  'stash-modal': lazy(() => import('./stashModal')),
  'grouped-card-picker': lazy(() => import('./groupedCardPicker')),
  'opponent-detail-modal': lazy(() => import('./opponentDetailModal')),
  'player-stash': lazy(() => import('./playerStash')),
  'board-chrome': lazy(() => import('./boardChrome')),
} as const;

export type DevPreviewKey = keyof typeof DEV_PREVIEWS;
