import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useGameClientIdentity } from '../hooks/useGameClientIdentity'
import { useGameView } from '../hooks/useGameView'
import { useGameSignalR } from '../hooks/useGameSignalR'
import { useGameLogAnnouncements } from '../hooks/useGameLogAnnouncements'
import { useSubmitCommand } from '../hooks/useSubmitCommand'
import { useIsPhoneLandscape, useIsMobilePortrait } from '../hooks/useLandscapeBreakpoint'
import { useToast } from '../components/Toast/useToast'
import type { GameAction, HandCardView, TokenAction } from '../api/types'
import { TOKEN_IMAGE_BY_ACTION } from './GameBoard/assetMaps'
import DayNightBackground from '../components/gameboard/DayNightBackground'
import GameBoardThemeToggle from '../components/gameboard/GameBoardThemeToggle'
import FullscreenToggleButton from '../components/gameboard/FullscreenToggleButton'
import TurnIndicator from '../components/gameboard/TurnIndicator'
import PhaseToggle from '../components/gameboard/PhaseToggle'
import OpponentRail from '../components/gameboard/OpponentRail'
import OpponentIndexTabs from '../components/gameboard/OpponentIndexTabs'
import DeckDiscardPiles from '../components/gameboard/DeckDiscardPiles'
import PlayerStash from '../components/gameboard/PlayerStash'
import PlayerHand from '../components/gameboard/PlayerHand'
import TokenTray from '../components/gameboard/TokenTray'
import RollStopControls from '../components/gameboard/RollStopControls'
import YumYumPrompt from '../components/gameboard/YumYumPrompt'
import StealPrompt from '../components/gameboard/StealPrompt'
import VictimPicker from '../components/gameboard/VictimPicker'
import FeeshCardPicker from '../components/gameboard/FeeshCardPicker'
import TokenPhasePanel from '../components/gameboard/TokenPhasePanel'
import BanditResponseModal from '../components/gameboard/BanditResponseModal'
import BanditWaitingModal from '../components/gameboard/BanditWaitingModal'
import GlassPanel from '../components/gameboard/GlassPanel'
import GameLogPanel from '../components/gameboard/GameLogPanel'
import GameLogButton from '../components/gameboard/GameLogButton'
import GameLogFocusPanel from '../components/gameboard/GameLogFocusPanel'
import PortraitOverlay from '../components/gameboard/PortraitOverlay'

type VictimPickerMode = 'shiny' | 'steal' | null

function GameBoardPage() {
  const { gameId } = useParams()
  const { identity } = useGameClientIdentity(gameId)
  const { showToast } = useToast()
  const isPhoneLandscape = useIsPhoneLandscape()
  const isMobilePortrait = useIsMobilePortrait()

  const [victimPickerMode, setVictimPickerMode] = useState<VictimPickerMode>(null)
  const [feeshPickerOpen, setFeeshPickerOpen] = useState(false)
  const [isGameLogOpen, setIsGameLogOpen] = useState(false)
  const gameLogButtonRef = useRef<HTMLButtonElement>(null)
  const wasGameLogOpenRef = useRef(false)

  // Close half of the game log's focus-trap contract (open half lives in GameLogFocusPanel,
  // which focuses its own close button on mount): once the panel unmounts, return keyboard focus
  // to the button that opened it. Guarded on the open->closed transition specifically (not just
  // "isGameLogOpen is false") so this doesn't try to focus the trigger on initial page load.
  useEffect(() => {
    if (wasGameLogOpenRef.current && !isGameLogOpen) {
      gameLogButtonRef.current?.focus()
    }
    wasGameLogOpenRef.current = isGameLogOpen
  }, [isGameLogOpen])

  const gameViewQuery = useGameView(gameId ?? '', identity?.seatIndex ?? -1)
  useGameSignalR(gameId ?? '', identity?.seatIndex ?? -1)
  useGameLogAnnouncements(gameViewQuery.data?.view.log ?? [], identity?.seatIndex ?? -1)
  const submitCommand = useSubmitCommand(gameId ?? '', identity?.seatIndex ?? -1)
  // TokenTray's `size` is a numeric prop, not a CSS class — Tailwind's phone-landscape variant
  // can't conditionally change a React prop value, so this is one of the few spots that genuinely
  // needs the JS-level breakpoint hook rather than a phone-landscape: utility class. Without this,
  // the tray rendered at its 64px desktop default on phone landscape too, and its footprint
  // overlapped the bottom of the hand's fanned/lifted cards. See Round 2 follow-up.
  // (isPhoneLandscape already hoisted above for portrait overlay check)

  // Tokens only appear in the tray when earned, so the browser won't have fetched them yet
  // on the roll that first produces each token type. Prefetch all six on mount so they're
  // already cached whenever the tray renders them.
  useEffect(() => {
    Object.values(TOKEN_IMAGE_BY_ACTION).forEach((src) => {
      const img = new Image()
      img.src = src
    })
  }, [])

  if (!gameId) {
    return null
  }

  if (!identity) {
    return (
      <section className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
        <h1>Game Board</h1>
        <p role="alert">Could not find your seat for this game. Try re-joining from the lobby.</p>
      </section>
    )
  }

  if (gameViewQuery.isLoading) {
    return (
      <section className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
        <h1>Game Board</h1>
        <p>Loading game…</p>
      </section>
    )
  }

  if (gameViewQuery.isError || !gameViewQuery.data) {
    return (
      <section className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
        <h1>Game Board</h1>
        <p role="alert">This game could not be found.</p>
      </section>
    )
  }

  if (isMobilePortrait) {
    return <PortraitOverlay />
  }

  const { view: gameView, allowedActions } = gameViewQuery.data
  const gameLog = gameView.log
  const localSeatIndex = identity.seatIndex
  const isLocalPlayerTurn = gameView.currentPlayerIndex === localSeatIndex
  const isPending = submitCommand.isPending

  function dispatch(request: Parameters<typeof submitCommand.mutate>[0]) {
    submitCommand.mutate(request, {
      onSuccess: (response) => {
        if (!response.succeeded) {
          showToast(response.errorMessage ?? 'That action was rejected.')
        } else if (response.infoMessage) {
          showToast(response.infoMessage, 'info')
        }
      },
    })
  }

  function handleAction(action: GameAction) {
    dispatch({ kind: 'action', playerSeat: localSeatIndex, action })
  }

  function handleCardPick(cardId: string) {
    dispatch({ kind: 'cardPick', playerSeat: localSeatIndex, cardId })
  }

  function handleDoubleStashSubmit(cardIds: string[]) {
    dispatch({ kind: 'doubleStash', playerSeat: localSeatIndex, cardIds })
  }

  function handleRecyclePick(replacement: TokenAction) {
    dispatch({ kind: 'recyclePick', playerSeat: localSeatIndex, replacement })
  }

  function handleFeeshPick(cardId: string) {
    dispatch({ kind: 'playFeesh', playerSeat: localSeatIndex, cardId })
    setFeeshPickerOpen(false)
  }

  // Routes a hand card's own PlayableAs verdict (per HandCardView's ranked-reason contract) to the
  // right handler — some actions need a follow-up picker (Feesh's discard choice, Shiny's victim
  // choice), others are plain single-shot actions. Only ever called with a non-null playableAs;
  // PlayerHand does not invoke this for unplayable cards.
  function handleHandCardActivate(card: HandCardView) {
    const action = card.playableAs
    if (!action) {
      return
    }

    switch (action) {
      case 'PlayFeesh':
      case 'PlayFeeshTokenPhase':
        setFeeshPickerOpen(true)
        break
      case 'PlayShiny':
      case 'PlayShinyTokenPhase':
        setVictimPickerMode('shiny')
        break
      default:
        handleAction(action)
    }
  }

  function handleVictimPick(victimSeat: number) {
    if (victimPickerMode === 'shiny') {
      dispatch({ kind: 'playShiny', playerSeat: localSeatIndex, victimSeat })
    } else if (victimPickerMode === 'steal') {
      dispatch({ kind: 'resolveTokenSteal', playerSeat: localSeatIndex, victimSeat })
    }
    setVictimPickerMode(null)
  }

  function handleStartSteal() {
    const opponentsWithCards = gameView.opponents.filter((opponent) => opponent.handCount > 0)
    if (opponentsWithCards.length > 0) {
      setVictimPickerMode('steal')
    } else {
      dispatch({ kind: 'resolveTokenSteal', playerSeat: localSeatIndex, victimSeat: null })
    }
  }

  const isLocalYumYumResponder =
    gameView.state === 'AwaitingYumYum' && gameView.yumYumResponderIndex === localSeatIndex

  const isAwaitingBanditResponse = gameView.tokenPhase?.step === 'BanditAwaitOpponentResponse'
  const isLocalBanditResponder =
    isAwaitingBanditResponse && gameView.tokenPhase!.banditCurrentResponderIndex === localSeatIndex

  return (
    <div className="gb-root">
      {/* Background wrapper for the phone-landscape game log focus modal (§B of the mobile
          landscape plan): everything that isn't itself a modal/overlay lives inside here so it can
          be blurred and locked as a single unit while the log panel is open. `absolute inset-0`
          (rather than a plain unstyled div) matters specifically because of the risk called out in
          the plan — once `filter` is applied below, this wrapper becomes the new containing block
          for every `position: fixed` descendant inside it (TurnIndicator, RollStopControls,
          PlayerHand, TokenPhasePanel, etc. all currently expect `fixed` to mean "relative to the
          viewport"). Giving the wrapper the exact same box as the viewport (its parent, `.gb-root`,
          is itself `position: fixed; inset: 0`, i.e. viewport-sized) means that becoming their
          containing block doesn't change where those descendants render, whether or not the filter
          is currently applied.
          DayNightBackground lives inside this wrapper (not as a separate sibling) so the scenery
          blurs along with everything else — per Round 2 Finding 4, the user's requirement is that
          everything but the log panel itself blurs, and a permanently-crisp background layer read
          as "inconsistent partial blur" rather than the intended uniform effect. It's purely
          decorative (`-z-10`, no interactive content), so `inert` has no functional effect on it.
          Modals/overlays that must stay sharp and interactive regardless of this wrapper's state —
          VictimPicker, FeeshCardPicker, BanditResponseModal, BanditWaitingModal, YumYumPrompt,
          StealPrompt, and (via a portal in Modal.tsx/OpponentDetailModal.tsx) OpponentDetailModal,
          StashModal, DiscardCarouselModal — are deliberately kept outside it. */}
      <div
        className="absolute inset-0"
        // `inert` (not just `pointer-events: none`) is what actually makes this the "only the log
        // accepts input" lock: pointer-events only blocks mouse/touch, but a keyboard user could
        // still Tab into this subtree and Enter-activate Roll/Stop/cards behind the blur without
        // it. `inert` removes the whole subtree from the tab order and blocks all interaction
        // (pointer and keyboard alike), which is exactly the native mechanism for this.
        inert={isGameLogOpen}
        style={
          isGameLogOpen
            ? { filter: 'blur(10px) saturate(0.6) brightness(0.55)', pointerEvents: 'none' }
            : undefined
        }
      >
        <DayNightBackground />
        <FullscreenToggleButton />
        <GameBoardThemeToggle />
        <GameLogButton ref={gameLogButtonRef} onClick={() => setIsGameLogOpen(true)} />
        <TurnIndicator currentPlayerName={gameView.currentPlayerName} isLocalPlayerTurn={isLocalPlayerTurn} state={gameView.state} />
        {isLocalPlayerTurn && <PhaseToggle state={gameView.state} />}

        <OpponentRail gameView={gameView} />
        <OpponentIndexTabs gameView={gameView} />
        <div className="fixed right-7 top-[110px] bottom-[523px] z-10 w-[320px] phone-landscape:hidden tablet-landscape:w-[260px]">
          <GameLogPanel entries={gameLog} />
        </div>
        <DeckDiscardPiles deckCount={gameView.deckCount} discardPile={gameView.discardPile} />
        <PlayerStash ownStash={gameView.ownStash} />
        <PlayerHand handCards={gameView.handCards} onCardActivate={handleHandCardActivate} />

        <div className="fixed bottom-6 left-1/2 z-10 -translate-x-1/2 phone-landscape:bottom-[3%]">
          <GlassPanel className="flex flex-col items-center gap-2 rounded-2xl px-6 py-3 phone-landscape:gap-0.5 phone-landscape:px-2 phone-landscape:py-1">
            <span className="text-xs font-semibold tracking-[0.12em] phone-landscape:text-[8px]" style={{ color: 'var(--gb-text-label)' }}>
              YOUR TOKENS
            </span>
            {/* gameView.phaseOneTokens/tokenPhase are single shared fields reflecting whichever
                player is CURRENTLY active, not "my own tokens" — every viewer's own tray must stay
                empty unless it's actually their turn, or everyone sees the active player's rolls
                duplicated into their own panel. The active player's tray is what OpponentTile shows
                to everyone else. */}
            <TokenTray
              phaseOneTokens={isLocalPlayerTurn ? gameView.phaseOneTokens : []}
              tokenPhase={isLocalPlayerTurn ? gameView.tokenPhase : null}
              isBusted={isLocalPlayerTurn && gameView.isBusted}
              size={isPhoneLandscape ? 26 : undefined}
            />
          </GlassPanel>
        </div>

        {isLocalPlayerTurn && !gameView.tokenPhase && !gameView.stealPhase && !isLocalYumYumResponder && (
          <RollStopControls allowedActions={allowedActions} onAction={handleAction} isPending={isPending} />
        )}

        {isLocalPlayerTurn && allowedActions.includes('PlayShiny') && (
          <button
            type="button"
            disabled={isPending}
            onClick={() => setVictimPickerMode('shiny')}
            className="fixed bottom-[170px] right-[80px] z-20 rounded-lg px-4 py-2 text-sm font-bold disabled:opacity-50 phone-landscape:bottom-[26%] phone-landscape:right-[2%] phone-landscape:px-2 phone-landscape:py-1 phone-landscape:text-[10px]"
            style={{ background: 'var(--gb-gold)', color: 'var(--gb-gold-text)' }}
          >
            Play Shiny
          </button>
        )}

        {isLocalPlayerTurn && gameView.tokenPhase && !isAwaitingBanditResponse && (
          <TokenPhasePanel
            tokenPhase={gameView.tokenPhase}
            allowedActions={allowedActions}
            isPending={isPending}
            onAction={handleAction}
            onCardPick={handleCardPick}
            onDoubleStashSubmit={handleDoubleStashSubmit}
            onRecyclePick={handleRecyclePick}
            onStartSteal={handleStartSteal}
          />
        )}
      </div>

      {isGameLogOpen && (
        <>
          {/* pointer-events: none on the wrapper above means it can't receive the "tap background
              to close" click itself — this full-screen invisible click-catcher sits in front of
              the (blurred, inert) wrapper but behind GameLogFocusPanel, so a tap anywhere outside
              the panel closes the log, and a tap on the panel itself doesn't (the panel is a later,
              higher z-indexed sibling, so it receives the click first and never bubbles down to
              this catcher for the area it covers). */}
          <div
            className="fixed inset-0 z-30 hidden phone-landscape:block"
            onClick={() => setIsGameLogOpen(false)}
            aria-hidden="true"
          />
          <GameLogFocusPanel entries={gameLog} onClose={() => setIsGameLogOpen(false)} />
        </>
      )}

      {isLocalYumYumResponder && (
        <YumYumPrompt allowedActions={allowedActions} onAction={handleAction} isPending={isPending} />
      )}

      {gameView.stealPhase && (
        <StealPrompt
          state={gameView.state}
          stealPhase={gameView.stealPhase}
          localSeatIndex={localSeatIndex}
          allowedActions={allowedActions}
          onAction={handleAction}
          onCardPick={handleCardPick}
          isPending={isPending}
        />
      )}

      {isLocalPlayerTurn && isAwaitingBanditResponse && <BanditWaitingModal />}

      {isLocalBanditResponder && (
        <BanditResponseModal
          revealedCardName={gameView.tokenPhase!.banditRevealedCardName!}
          stashableCards={gameView.tokenPhase!.stashableHandCardsForCurrentPrompt}
          onStash={handleCardPick}
          onPass={() => handleAction('TokenBanditMatchPass')}
          isPending={isPending}
        />
      )}

      {victimPickerMode && (
        <VictimPicker
          title={victimPickerMode === 'shiny' ? 'Play Shiny — steal from a stash' : 'Steal from a hand'}
          opponents={
            victimPickerMode === 'steal'
              ? gameView.opponents.filter((opponent) => opponent.handCount > 0)
              : gameView.opponents
          }
          onPick={handleVictimPick}
          onClose={() => setVictimPickerMode(null)}
          isPending={isPending}
        />
      )}

      {feeshPickerOpen && (
        <FeeshCardPicker
          discardPile={gameView.discardPile}
          onPick={handleFeeshPick}
          onClose={() => setFeeshPickerOpen(false)}
          isPending={isPending}
        />
      )}
    </div>
  )
}

export default GameBoardPage
