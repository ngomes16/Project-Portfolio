/**
 * File: src/utils/images.ts
 * Purpose: Provide representative destination imagery using curated Unsplash URLs
 *          based on a destination string. These are used as sample photos in
 *          the Home screen and trip cards until users attach their own images.
 */

export function getDestinationImage(destination?: string): string {
  const d = (destination || '').toLowerCase();
  const baseParams = '?auto=format&fit=crop&w=1200&q=60';
  const candidates: [RegExp, string][] = [
    [/new york|nyc|liberty|statue/, 'https://images.unsplash.com/photo-1523731407965-2430cd12f5e4'],
    [/beach|canc|island|malibu|hawaii|bahamas/, 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e'],
    [/japan|tokyo|kyoto|fuji|mt\s*fuji|osaka/, 'https://images.unsplash.com/photo-1504610926078-a1611febcad3'],
    [/chicago|illinois|chi-town|chi/, 'https://images.unsplash.com/photo-1484249170766-998fa6efe3c0'],
    [/ski|aspen|snow|alps|mountain|resort/, 'https://images.unsplash.com/photo-1482192505345-5655af888cc4'],
  ];
  for (const [re, url] of candidates) {
    if (re.test(d)) return url + baseParams;
  }
  // Fallback to a pleasant coastline scene
  return 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e' + baseParams;
}


