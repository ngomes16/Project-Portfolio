/**
 * File: src/utils/budget.ts
 * Purpose: Budget utilities for aggregating categories and providing consistent colors.
 */
import { BudgetItem, BudgetCategory } from '../data/sample';

export function categoryColor(category: BudgetCategory): string {
  switch (category) {
    case 'Lodging':
      return '#7C5CFF';
    case 'Flights':
      return '#0EA5E9';
    case 'Transport':
      return '#10B981';
    case 'Activities':
      return '#F59E0B';
    case 'Food':
      return '#EF4444';
    default:
      return '#94A3B8';
  }
}

export function categoryTotals(items: BudgetItem[]): { category: BudgetCategory; total: number }[] {
  const map: Record<BudgetCategory, number> = {
    Lodging: 0,
    Flights: 0,
    Transport: 0,
    Activities: 0,
    Food: 0,
    Other: 0,
  };
  for (const it of items) {
    const key = (it.category ?? 'Other') as BudgetCategory;
    map[key] += it.total;
  }
  return Object.entries(map)
    .filter(([, total]) => total > 0)
    .map(([category, total]) => ({ category: category as BudgetCategory, total }));
}


