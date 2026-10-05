import type { OwnStashView } from '../../api/types';
import PlayerStash from '../../components/gameboard/PlayerStash';

const OWN_STASH: OwnStashView = {
  faceDownCards: [
    { cardId: '1', name: 'Nanners' },
    { cardId: '2', name: 'Blammo' },
  ],
  faceUpCards: [
    { cardId: '3', name: 'Feesh' },
    { cardId: '4', name: 'Shiny' },
  ],
};

/** Renders the player's face-down/face-up stash piles at their real fixed board position, for
 * checking the CardCountBadge dead-click-zone fix at the bottom-right corner of each card. */
function PlayerStashPreview() {
  return <PlayerStash ownStash={OWN_STASH} />;
}

export default PlayerStashPreview;
