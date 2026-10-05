import { useSearchParams } from 'react-router-dom';
import type { CardName } from '../../api/types';
import StashModal from '../../components/gameboard/StashModal';

const ALL_CARD_NAMES: CardName[] = ['Blammo', 'Nanners', 'Feesh', 'Shiny', 'Yumyum', 'MmmPie', 'Kitteh', 'Doggo'];

/** Boundary card-count states worth checking for this component: none, a single card, exactly
 * one full row, a partial second row, and the max possible (one of every distinct CardName). */
function cardsFor(scenario: string | null) {
  switch (scenario) {
    case 'empty':
      return [];
    case 'one':
      return [{ cardId: '1', name: 'Nanners' as CardName }];
    case 'three':
      return [
        { cardId: '1', name: 'Nanners' as CardName },
        { cardId: '2', name: 'Blammo' as CardName },
        { cardId: '3', name: 'Feesh' as CardName },
      ];
    case 'five':
      return [
        { cardId: '1', name: 'Nanners' as CardName },
        { cardId: '2', name: 'Nanners' as CardName },
        { cardId: '3', name: 'Blammo' as CardName },
        { cardId: '4', name: 'Feesh' as CardName },
        { cardId: '5', name: 'Shiny' as CardName },
      ];
    case 'allDistinct':
      return ALL_CARD_NAMES.map((name, i) => ({ cardId: String(i + 1), name }));
    default:
      return [
        { cardId: '1', name: 'Nanners' as CardName },
        { cardId: '2', name: 'Nanners' as CardName },
        { cardId: '3', name: 'Nanners' as CardName },
        { cardId: '4', name: 'Blammo' as CardName },
        { cardId: '5', name: 'Blammo' as CardName },
        { cardId: '6', name: 'Feesh' as CardName },
        { cardId: '7', name: 'Shiny' as CardName },
        { cardId: '8', name: 'Kitteh' as CardName },
      ];
  }
}

/** ?scenario=empty|one|three|five|allDistinct (default: an 8-card/5-group mix). */
function StashModalPreview() {
  const [searchParams] = useSearchParams();
  const cards = cardsFor(searchParams.get('scenario'));

  return <StashModal title="Your Face-Down Stash" cards={cards} onClose={() => {}} />;
}

export default StashModalPreview;
