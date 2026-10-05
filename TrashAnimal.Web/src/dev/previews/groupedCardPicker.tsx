import { useSearchParams } from 'react-router-dom';
import type { CardName } from '../../api/types';
import GroupedCardPicker from '../../components/gameboard/GroupedCardPicker';

const ALL_CARD_NAMES: CardName[] = ['Blammo', 'Nanners', 'Feesh', 'Shiny', 'Yumyum', 'MmmPie', 'Kitteh', 'Doggo'];

function cardsFor(scenario: string | null) {
  switch (scenario) {
    case 'empty':
      return [];
    case 'one':
      return [{ cardId: '1', name: 'Nanners' as CardName }];
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

/** ?scenario=empty|one|four|allDistinct (default: four distinct groups — a short trailing row). */
function GroupedCardPickerPreview() {
  const [searchParams] = useSearchParams();
  const cards = cardsFor(searchParams.get('scenario'));

  return (
    <div style={{ padding: 24, maxWidth: 520 }}>
      <GroupedCardPicker cards={cards} min={0} max={cards.length} isPending={false} onConfirm={() => {}} />
    </div>
  );
}

export default GroupedCardPickerPreview;
