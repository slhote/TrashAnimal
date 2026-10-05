import type { ReactNode } from 'react';

interface CardCountBadgeProps {
  count: number;
  /** Size tier for the badge circle + text. Each tier includes a phone-landscape variant unless
   * `includeResponsive` is false. Tiers match the sizes already in use across the gameboard
   * (preserved exactly, not renormalized, to avoid a visual-regression diff on extraction):
   * 'small' — GroupedCardPicker's dense grid; 'medium' — single/simple badges (Bandit response,
   * opponent detail); 'compact' — StashModal's larger card grid; 'large' — PlayerStash's
   * face-down/face-up piles. Default: 'medium'. */
  size?: 'small' | 'medium' | 'compact' | 'large';
  /** Badge color scheme. Default: 'gold'. */
  color?: 'gold' | 'green';
  /** Whether to include the `phone-landscape:` responsive size variant. Default: true. */
  includeResponsive?: boolean;
  /** The element the badge decorates — an image, button, or any other content. */
  children: ReactNode;
}

const SIZE_CLASSES: Record<NonNullable<CardCountBadgeProps['size']>, { base: string; responsive: string }> = {
  small: {
    base: 'h-6 w-6 text-[10px]',
    responsive: 'phone-landscape:h-5 phone-landscape:w-5 phone-landscape:text-[9px]',
  },
  medium: {
    base: 'h-6 w-6 text-xs',
    responsive: '',
  },
  compact: {
    base: 'h-7 w-7 text-xs',
    responsive: 'phone-landscape:h-6 phone-landscape:w-6 phone-landscape:text-[10px]',
  },
  large: {
    base: 'h-9 w-9 text-xs',
    responsive: 'phone-landscape:h-7 phone-landscape:w-7 phone-landscape:text-[10px]',
  },
};

const COLOR_STYLES: Record<NonNullable<CardCountBadgeProps['color']>, { background: string; color: string; borderColor: string }> = {
  gold: {
    background: 'var(--gb-gold)',
    color: 'var(--gb-gold-text)',
    borderColor: 'var(--gb-gold-text-dark)',
  },
  green: {
    background: 'var(--gb-green)',
    color: 'var(--gb-green-text)',
    borderColor: 'var(--gb-green-text)',
  },
};

/** Wraps `children` (a card image, button, or other element) with an absolutely-positioned
 * corner badge showing `count` — the count/card pairing shared by StashModal, GroupedCardPicker,
 * OpponentDetailModal, BanditResponseModal, and PlayerStash. Always renders `children` inside a
 * `relative w-fit` wrapper it owns, so the badge's `-bottom-2 -right-2` overhang is included in
 * the wrapper's own box size — this is what keeps shrink-to-fit ancestors and scroll containers
 * from silently clipping the badge (see the phone-landscape StashModal fix this component
 * generalizes). Don't reposition the badge or re-wrap `children` at the call site instead of
 * using this component — that reintroduces the exact bug this exists to prevent. */
function CardCountBadge({ count, size = 'medium', color = 'gold', includeResponsive = true, children }: CardCountBadgeProps) {
  const sizeClasses = SIZE_CLASSES[size];
  const colorStyles = COLOR_STYLES[color];

  return (
    <div className="relative w-fit">
      {children}
      <span
        className={`pointer-events-none absolute -bottom-2 -right-2 flex items-center justify-center rounded-full border-2 font-bold ${sizeClasses.base} ${includeResponsive ? sizeClasses.responsive : ''}`}
        style={colorStyles}
      >
        {count}
      </span>
    </div>
  );
}

export default CardCountBadge;
