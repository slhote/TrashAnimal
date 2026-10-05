import { useState } from 'react';
import type { CardName } from '../../api/types';
import { CARD_IMAGE_BY_NAME } from '../../pages/GameBoard/assetMaps';
import CardCountBadge from './CardCountBadge';

interface PickableCard {
  cardId: string;
  name: CardName;
}

interface GroupedCardPickerProps {
  cards: PickableCard[];
  min: number;
  max: number;
  isPending: boolean;
  onConfirm: (cardIds: string[]) => void;
  confirmLabelPrefix?: string;
}

/** Groups a flat card list by name and renders +/− per-group counters capped by `max`.
 * Always requires an explicit confirm click — no auto-submit on `+`, even at min===max===1. */
function GroupedCardPicker({
  cards,
  min,
  max,
  isPending,
  onConfirm,
  confirmLabelPrefix = 'Stash',
}: GroupedCardPickerProps) {
  const groupedIds = new Map<CardName, string[]>();
  for (const card of cards) {
    const existing = groupedIds.get(card.name) ?? [];
    existing.push(card.cardId);
    groupedIds.set(card.name, existing);
  }

  const [selected, setSelected] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    for (const name of groupedIds.keys()) initial[name] = 0;
    return initial;
  });

  const totalSelected = Object.values(selected).reduce((sum, n) => sum + n, 0);

  const entries = [...groupedIds.entries()];

  function increment(name: CardName) {
    const groupSize = groupedIds.get(name)?.length ?? 0;
    if (totalSelected >= max || (selected[name] ?? 0) >= groupSize) return;
    setSelected((prev) => ({ ...prev, [name]: (prev[name] ?? 0) + 1 }));
  }

  function decrement(name: CardName) {
    if ((selected[name] ?? 0) <= 0) return;
    setSelected((prev) => ({ ...prev, [name]: (prev[name] ?? 0) - 1 }));
  }

  function handleConfirm() {
    const cardIds: string[] = [];
    for (const [name, count] of Object.entries(selected)) {
      const ids = groupedIds.get(name as CardName) ?? [];
      cardIds.push(...ids.slice(0, count));
    }
    onConfirm(cardIds);
    setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, 0])));
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid max-h-[60vh] grid-cols-3 gap-4 overflow-y-auto pb-2 pr-2 phone-landscape:max-h-[calc(100vh-220px)] phone-landscape:gap-2">
        {entries.map(([name, ids]) => {
          const count = selected[name] ?? 0;
          const canIncrement = count < ids.length && totalSelected < max;
          return (
            <div key={name} className="flex flex-col items-center gap-1">
              <CardCountBadge count={ids.length} size="small">
                <img
                  src={CARD_IMAGE_BY_NAME[name]}
                  alt={name}
                  className="h-[120px] w-[86px] rounded-lg object-cover phone-landscape:h-[72px] phone-landscape:w-[52px]"
                  style={{ opacity: 1 }}
                />
              </CardCountBadge>
              <p className="text-[11px] font-medium phone-landscape:text-[10px]" style={{ color: 'var(--gb-text-primary)' }}>
                {name}
              </p>
              <div className="-mt-1 flex flex-col items-center gap-1">
                <p className="text-[10px]" style={{ color: 'var(--gb-text-label)' }}>
                  {count} / {ids.length}
                </p>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => decrement(name)}
                    disabled={isPending || count <= 0}
                    aria-label={`Remove ${name}`}
                    className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold disabled:opacity-40 phone-landscape:h-6 phone-landscape:w-6"
                    style={{ background: 'rgba(255,255,255,.22)', border: '1.5px solid rgba(255,255,255,.5)', color: 'var(--gb-text-primary)' }}
                  >
                    −
                  </button>
                  <button
                    type="button"
                    onClick={() => increment(name)}
                    disabled={isPending || !canIncrement}
                    aria-label={`Add ${name}`}
                    className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold disabled:opacity-40 phone-landscape:h-6 phone-landscape:w-6"
                    style={{ background: 'rgba(255,255,255,.22)', border: '1.5px solid rgba(255,255,255,.5)', color: 'var(--gb-text-primary)' }}
                  >
                    +
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <button
        type="button"
        disabled={isPending || totalSelected < min}
        onClick={handleConfirm}
        className="self-center rounded-lg px-4 py-2 text-sm font-bold disabled:opacity-50"
        style={{ background: 'var(--gb-green)', color: 'var(--gb-green-text)' }}
      >
        {confirmLabelPrefix} {totalSelected} card{totalSelected === 1 ? '' : 's'}
      </button>
    </div>
  );
}

export default GroupedCardPicker;
