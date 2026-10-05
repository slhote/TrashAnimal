import { useSearchParams } from 'react-router-dom';
import type { CardName, OpponentSummaryView } from '../../api/types';
import OpponentDetailModal from '../../components/gameboard/OpponentDetailModal';

const ALL_CARD_NAMES: CardName[] = ['Blammo', 'Nanners', 'Feesh', 'Shiny', 'Yumyum', 'MmmPie', 'Kitteh', 'Doggo'];

function stashFor(scenario: string | null) {
  switch (scenario) {
    case 'empty':
      return [];
    case 'four':
      return [
        { cardId: '1', name: 'Nanners' as CardName },
        { cardId: '2', name: 'Blammo' as CardName },
        { cardId: '3', name: 'Feesh' as CardName },
        { cardId: '4', name: 'Shiny' as CardName },
      ];
    case 'allDistinct':
      return ALL_CARD_NAMES.map((name, i) => ({ cardId: String(i + 1), name }));
    default:
      return [
        { cardId: '1', name: 'Nanners' as CardName },
        { cardId: '2', name: 'Blammo' as CardName },
        { cardId: '3', name: 'Feesh' as CardName },
        { cardId: '4', name: 'Shiny' as CardName },
      ];
  }
}

/** ?scenario=empty|four|allDistinct (default: four distinct groups — a short trailing row). */
function OpponentDetailModalPreview() {
  const [searchParams] = useSearchParams();
  const opponent: OpponentSummaryView = {
    seatIndex: 0,
    name: 'Rocket',
    handCount: 3,
    stashFaceDownCount: 2,
    stashFaceUpCards: stashFor(searchParams.get('scenario')),
  };

  return <OpponentDetailModal opponents={[opponent]} selectedIndex={0} onSelectIndex={() => {}} onClose={() => {}} />;
}

export default OpponentDetailModalPreview;
