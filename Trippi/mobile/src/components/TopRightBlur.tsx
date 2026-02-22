/**
 * File: src/components/TopRightBlur.tsx
 * Purpose: Decorative, lightweight radial purple blur rendered with react-native-svg.
 *          Anchors to the top-right corner and softly fades to transparent.
 * Update: Increase size and move further into the corner so it originates from the
 *         very top-right offscreen area. This prevents visible clipping at the
 *         top/left and ensures the gradient appears to emanate from the corner.
 */
import React from 'react';
import { View } from 'react-native';
import Svg, { Defs, RadialGradient, Stop, Rect } from 'react-native-svg';

export function TopRightBlur() {
  return (
    <View pointerEvents="none" style={{ position: 'absolute', right: -80, top: -80, width: '85%', height: 320 }}>
      <Svg width="100%" height="100%">
        <Defs>
          <RadialGradient id="tr-blur" cx="100%" cy="0%" r="100%">
            <Stop offset="0%" stopColor="#EAE2FF" stopOpacity="0.9" />
            <Stop offset="55%" stopColor="#EAE2FF" stopOpacity="0.25" />
            <Stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
          </RadialGradient>
        </Defs>
        <Rect x="0" y="0" width="100%" height="100%" fill="url(#tr-blur)" />
      </Svg>
    </View>
  );
}

export default TopRightBlur;


