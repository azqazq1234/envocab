export const PAGE_SIZES = [10, 20, 50, 100] as const;

export function fittingPageSize(
  availableHeight: number,
  headerHeight: number,
  rowHeight: number,
): number {
  if (rowHeight <= 0 || availableHeight <= headerHeight) return 10;
  const capacity = Math.floor((availableHeight - headerHeight) / rowHeight);
  // Advance once the viewport fits at least two rows beyond the lower tier.
  return PAGE_SIZES.find((size) => capacity <= size + 1) ?? PAGE_SIZES.at(-1)!;
}
