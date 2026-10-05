import type { StashableHandCard } from '../../api/types';
import { CARD_IMAGE_BY_NAME } from '../../pages/GameBoard/assetMaps';
import CardCountBadge from './CardCountBadge';
import Modal from './Modal';

interface StashModalProps {
  title: string;
  cards: StashableHandCard[];
  onClose: () => void;
}

/** Groups a list of fully-identified stash cards by CardName with a count badge, sorted
 * highest-count-first — shared by the player's own face-up stash modal, their own face-down stash
 * modal (identity isn't hidden from the owner, only from opponents), and the opponent-detail
 * modal's stash section. */
function StashModal({ title, cards, onClose }: StashModalProps) {
  const grouped = new Map<string, number>();
  for (const card of cards) {
    grouped.set(card.name, (grouped.get(card.name) ?? 0) + 1);
  }
  const entries = [...grouped.entries()].sort((a, b) => b[1] - a[1]);

  return (
    <Modal
      onClose={onClose}
      labelledBy="stash-modal-heading"
      maxWidthClassName="max-w-[392px] phone-landscape:max-w-[228px]"
    >
      <h2
        id="stash-modal-heading"
        className="mb-1 pr-5 text-lg font-semibold phone-landscape:mb-0 phone-landscape:pr-4 phone-landscape:text-sm"
        style={{ color: 'var(--gb-text-primary)' }}
      >
        {title}
      </h2>
      <p className="mb-6 text-xs tracking-[0.06em] phone-landscape:mb-1" style={{ color: 'var(--gb-text-label)' }}>
        {cards.length} TOTAL
      </p>
      <div className="grid max-h-[60vh] grid-cols-3 gap-3 overflow-y-auto pb-2 pr-2 phone-landscape:max-h-[calc(100vh-100px)] phone-landscape:gap-2">
        {entries.map(([name, count]) => (
          <CardCountBadge key={name} count={count} size="compact">
            <img
              src={CARD_IMAGE_BY_NAME[name as keyof typeof CARD_IMAGE_BY_NAME]}
              alt={name}
              className="h-[140px] w-[100px] rounded-lg object-cover phone-landscape:h-[78px] phone-landscape:w-[56px]"
            />
          </CardCountBadge>
        ))}
        {entries.length === 0 && <p style={{ color: 'var(--gb-text-label)' }}>Nothing here yet.</p>}
      </div>
    </Modal>
  );
}

export default StashModal;
