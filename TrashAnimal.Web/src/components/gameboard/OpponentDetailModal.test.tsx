import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../test/test-utils';
import type { OpponentSummaryView, StashableHandCard } from '../../api/types';
import OpponentDetailModal from './OpponentDetailModal';

function card(cardId: string, name: StashableHandCard['name']): StashableHandCard {
  return { cardId, name };
}

function buildOpponent(overrides: Partial<OpponentSummaryView> = {}): OpponentSummaryView {
  return {
    seatIndex: 0,
    name: 'Alex',
    handCount: 3,
    stashFaceDownCount: 2,
    stashFaceUpCards: [],
    ...overrides,
  };
}

describe('OpponentDetailModal', () => {
  it('groups face-up stash cards by name with a count badge', () => {
    // Distinct from stashFaceDownCount/handCount so the count badges' text doesn't collide with
    // the header stat boxes' own numbers.
    const opponent = buildOpponent({
      handCount: 9,
      stashFaceDownCount: 8,
      stashFaceUpCards: [card('a', 'Nanners'), card('b', 'Nanners'), card('c', 'Blammo')],
    });
    render(
      <OpponentDetailModal opponents={[opponent]} selectedIndex={0} onSelectIndex={vi.fn()} onClose={vi.fn()} />,
    );

    expect(screen.getAllByRole('img')).toHaveLength(2);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows the empty state when the opponent has no face-up stash', () => {
    const opponent = buildOpponent({ stashFaceUpCards: [] });
    render(
      <OpponentDetailModal opponents={[opponent]} selectedIndex={0} onSelectIndex={vi.fn()} onClose={vi.fn()} />,
    );

    expect(screen.getByText('Nothing here yet.')).toBeInTheDocument();
  });

  it('lays out card groups in a 3-column grid regardless of count', () => {
    const opponent = buildOpponent({
      stashFaceUpCards: [
        card('a', 'Nanners'),
        card('b', 'Blammo'),
        card('c', 'MmmPie'),
        card('d', 'Feesh'),
      ],
    });
    render(
      <OpponentDetailModal opponents={[opponent]} selectedIndex={0} onSelectIndex={vi.fn()} onClose={vi.fn()} />,
    );

    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(4);
    const grid = images[0].closest('.grid');
    expect(grid).toHaveClass('grid-cols-3');
    for (const img of images) {
      expect(img.closest('.grid')).toBe(grid);
    }
  });

  it('does not render prev/next navigation when there is only one opponent', () => {
    const opponent = buildOpponent();
    render(
      <OpponentDetailModal opponents={[opponent]} selectedIndex={0} onSelectIndex={vi.fn()} onClose={vi.fn()} />,
    );

    expect(screen.queryByRole('button', { name: /previous opponent/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /next opponent/i })).not.toBeInTheDocument();
  });
});
