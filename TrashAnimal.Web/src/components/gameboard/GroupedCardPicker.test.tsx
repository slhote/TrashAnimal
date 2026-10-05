import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen } from '../../test/test-utils';
import GroupedCardPicker from './GroupedCardPicker';
import type { StashableHandCard } from '../../api/types';

function card(cardId: string, name: StashableHandCard['name']): StashableHandCard {
  return { cardId, name };
}

describe('GroupedCardPicker', () => {
  it('collapses duplicate card names into one tile with the correct pool count', () => {
    render(
      <GroupedCardPicker
        cards={[card('a', 'Nanners'), card('b', 'Nanners'), card('c', 'Blammo')]}
        min={1}
        max={2}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );

    // Two distinct tiles
    expect(screen.getAllByRole('img').length).toBe(2);
    // Pool count badges — "2" for Nanners, "1" for Blammo
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('increments and decrements per-group selection within per-card cap', async () => {
    const user = userEvent.setup();
    render(
      <GroupedCardPicker
        cards={[card('a', 'Nanners'), card('b', 'Nanners')]}
        min={0}
        max={2}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add nanners/i }));
    expect(screen.getByText('1 / 2')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /add nanners/i }));
    expect(screen.getByText('2 / 2')).toBeInTheDocument();

    // At cap — Add disabled
    expect(screen.getByRole('button', { name: /add nanners/i })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /remove nanners/i }));
    expect(screen.getByText('1 / 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add nanners/i })).not.toBeDisabled();
  });

  it('enforces the overall max across groups', async () => {
    const user = userEvent.setup();
    render(
      <GroupedCardPicker
        cards={[card('a', 'Nanners'), card('b', 'Blammo')]}
        min={0}
        max={1}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: /add nanners/i }));
    // Overall max=1 hit — Add Blammo should now be disabled
    expect(screen.getByRole('button', { name: /add blammo/i })).toBeDisabled();
  });

  it('passes the correct cardIds to onConfirm, resolving by insertion order', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <GroupedCardPicker
        cards={[card('id-1', 'Nanners'), card('id-2', 'Nanners'), card('id-3', 'Blammo')]}
        min={1}
        max={2}
        isPending={false}
        onConfirm={onConfirm}
      />,
    );

    // Select 1 Nanners, 1 Blammo
    await user.click(screen.getByRole('button', { name: /add nanners/i }));
    await user.click(screen.getByRole('button', { name: /add blammo/i }));
    await user.click(screen.getByRole('button', { name: /stash 2 cards/i }));

    expect(onConfirm).toHaveBeenCalledWith(['id-1', 'id-3']);
  });

  it('disables confirm when selection is below min', async () => {
    const user = userEvent.setup();
    render(
      <GroupedCardPicker
        cards={[card('a', 'Nanners')]}
        min={1}
        max={1}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );

    // min=1, nothing selected yet
    expect(screen.getByRole('button', { name: /stash 0 cards/i })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /add nanners/i }));
    expect(screen.getByRole('button', { name: /stash 1 card/i })).not.toBeDisabled();
  });

  it('disables all controls when isPending', () => {
    render(
      <GroupedCardPicker
        cards={[card('a', 'Nanners')]}
        min={0}
        max={1}
        isPending={true}
        onConfirm={vi.fn()}
      />,
    );

    for (const btn of screen.getAllByRole('button')) {
      expect(btn).toBeDisabled();
    }
  });

  it('lays out card groups in a 3-column grid regardless of count', () => {
    render(
      <GroupedCardPicker
        cards={[
          card('a', 'Nanners'),
          card('b', 'Blammo'),
          card('c', 'MmmPie'),
          card('d', 'Feesh'),
        ]}
        min={0}
        max={4}
        isPending={false}
        onConfirm={vi.fn()}
      />,
    );

    // 4 distinct groups laid out in a grid so a short trailing row still spans the full width
    // instead of centering as an isolated cluster.
    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(4);
    const grid = images[0].closest('.grid');
    expect(grid).toHaveClass('grid-cols-3');
    for (const img of images) {
      expect(img.closest('.grid')).toBe(grid);
    }
  });
});
