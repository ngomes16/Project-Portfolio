/**
 * File: web/src/utils/colors.js
 * Purpose: Provide color utilities used by charts and avatars.
 */
export const CATEGORY_COLORS = {
  Lodging: '#7C5CFF',
  Flights: '#0EA5E9',
  Transport: '#10B981',
  Activities: '#F59E0B',
  Food: '#EF4444',
  Other: '#94A3B8',
};

export function colorFor(category) {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.Other;
}


