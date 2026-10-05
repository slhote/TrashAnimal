import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../test/test-utils';
import type { StashableHandCard } from '../../api/types';
import StashModal from './StashModal';

function card(cardId: string, name: StashableHandCard['name']): StashableHandCard {
  return { cardId, name };
}

describe('StashModal', () => {
  it('groups cards by name with a count badge', () => {
    render(
      <StashModal
        title="Your stash"
        cards={[card('a', 'Nanners'), card('b', 'Nanners'), card('c', 'Blammo')]}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getAllByRole('img')).toHaveLength(2);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows the empty state when there are no cards', () => {
    render(<StashModal title="Your stash" cards={[]} onClose={vi.fn()} />);

    expect(screen.getByText('Nothing here yet.')).toBeInTheDocument();
  });

  it('lays out card groups in a 3-column grid regardless of count', () => {
    render(
      <StashModal
        title="Your stash"
        cards={[
          card('a', 'Nanners'),
          card('b', 'Blammo'),
          card('c', 'MmmPie'),
          card('d', 'Feesh'),
        ]}
        onClose={vi.fn()}
      />,
    );

    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(4);
    const grid = images[0].closest('.grid');
    expect(grid).toHaveClass('grid-cols-3');
    for (const img of images) {
      expect(img.closest('.grid')).toBe(grid);
    }
  });
});
