import { createPortal } from 'react-dom';
import type { OpponentSummaryView } from '../../api/types';
import { CARD_IMAGE_BY_NAME, opponentColorForSeat } from '../../pages/GameBoard/assetMaps';
import CardCountBadge from './CardCountBadge';
import Modal from './Modal';

interface OpponentDetailModalProps {
  opponents: OpponentSummaryView[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  onClose: () => void;
}

function OpponentDetailModal({ opponents, selectedIndex, onSelectIndex, onClose }: OpponentDetailModalProps) {
  const opponent = opponents[selectedIndex];

  const grouped = new Map<string, number>();
  for (const card of opponent.stashFaceUpCards) {
    grouped.set(card.name, (grouped.get(card.name) ?? 0) + 1);
  }
  const entries = [...grouped.entries()].sort((a, b) => b[1] - a[1]);

  const hasMultipleOpponents = opponents.length > 1;

  // Portaled to document.body, same reasoning as Modal.tsx's own portal: this component is
  // rendered nested inside OpponentRail/OpponentIndexTabs, both of which live inside
  // GameBoardPage's phone-landscape game-log blur/lock wrapper. Modal.tsx already escapes that
  // wrapper via its own portal, but the prev/next carousel buttons below are siblings of <Modal>,
  // not children of it, so without this portal they'd stay nested in the filtered subtree and
  // could get blurred/made inert independently of the modal content itself.
  return createPortal(
    <>
      {/* Modal itself is position:fixed, so it isn't part of any sibling flex layout's normal
          flow — nesting these buttons in a flex row alongside it just centers the two buttons
          together (over the modal) instead of pinning them to the viewport edges. Position them
          as their own fixed elements instead. */}
      {hasMultipleOpponents && (
        <button
          type="button"
          onClick={() => onSelectIndex((selectedIndex - 1 + opponents.length) % opponents.length)}
          aria-label="Previous opponent"
          className="gb-glass fixed left-10 top-1/2 z-50 flex h-[52px] w-[52px] -translate-y-1/2 items-center justify-center rounded-full text-xl"
          style={{ color: 'var(--gb-text-primary)' }}
        >
          ‹
        </button>
      )}

      <Modal onClose={onClose} labelledBy="opponent-modal-heading" maxWidthClassName="max-w-[620px]">
        <div className="mb-4 flex items-center gap-3">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold"
            style={{ background: opponentColorForSeat(opponent.seatIndex), color: 'var(--gb-text-on-avatar)' }}
          >
            {opponent.name.charAt(0).toUpperCase()}
          </span>
          <h2 id="opponent-modal-heading" className="text-lg font-semibold" style={{ color: 'var(--gb-text-primary)' }}>
            {opponent.name}
          </h2>
        </div>

        <div className="mb-4 flex gap-4">
          <div className="gb-glass flex-1 rounded-xl px-4 py-3 text-center">
            <p className="text-2xl font-bold" style={{ color: 'var(--gb-gold)' }}>
              {opponent.stashFaceDownCount}
            </p>
            <p className="text-xs" style={{ color: 'var(--gb-text-label)' }}>
              Face-down stash
            </p>
          </div>
          <div className="gb-glass flex-1 rounded-xl px-4 py-3 text-center">
            <p className="text-2xl font-bold" style={{ color: 'var(--gb-green)' }}>
              {opponent.handCount}
            </p>
            <p className="text-xs" style={{ color: 'var(--gb-text-label)' }}>
              Cards in hand
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-[0.12em]" style={{ color: 'var(--gb-text-label)' }}>
            FACE-UP STASH
          </span>
          <span
            className="rounded-full border px-2 py-0.5 text-[11px] font-bold"
            style={{ background: 'rgba(8,14,28,.7)', borderColor: 'rgba(255,255,255,.25)', color: 'var(--gb-text-primary)' }}
          >
            {opponent.stashFaceUpCards.length} TOTAL
          </span>
        </div>
        <div className="mt-3 grid max-h-[60vh] grid-cols-3 gap-3 overflow-y-auto pb-2 pr-2 phone-landscape:max-h-[calc(100vh-260px)]">
          {entries.map(([name, count]) => (
            <CardCountBadge key={name} count={count} size="medium" includeResponsive={false}>
              <img
                src={CARD_IMAGE_BY_NAME[name as keyof typeof CARD_IMAGE_BY_NAME]}
                alt={name}
                className="h-[120px] w-[86px] rounded-lg object-cover"
              />
            </CardCountBadge>
          ))}
          {entries.length === 0 && <p style={{ color: 'var(--gb-text-label)' }}>Nothing here yet.</p>}
        </div>
      </Modal>

      {hasMultipleOpponents && (
        <button
          type="button"
          onClick={() => onSelectIndex((selectedIndex + 1) % opponents.length)}
          aria-label="Next opponent"
          className="gb-glass fixed right-10 top-1/2 z-50 flex h-[52px] w-[52px] -translate-y-1/2 items-center justify-center rounded-full text-xl"
          style={{ color: 'var(--gb-text-primary)' }}
        >
          ›
        </button>
      )}
    </>,
    document.body,
  );
}

export default OpponentDetailModal;
