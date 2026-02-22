/**
 * File: src/components/create-trip/WizardContainer.tsx
 * Purpose: Container that orchestrates page transitions for the Create Trip wizard. Provides
 *          slide/fade animations between steps with Previous/Next actions.
 */
import React, { useEffect, useState } from 'react';
import { View, Animated, Easing, LayoutChangeEvent } from 'react-native';

type Props = {
  index: number; // current step index
  children: React.ReactNode[]; // pages
};

export function WizardContainer({ index, children }: Props) {
  const [containerWidth, setContainerWidth] = useState(0);
  const translateX = React.useRef(new Animated.Value(0)).current;
  const opacity = React.useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!containerWidth) return;
    Animated.parallel([
      Animated.timing(translateX, { toValue: -index * containerWidth, duration: 260, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.88, duration: 120, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 1, duration: 140, useNativeDriver: true }),
      ]),
    ]).start();
  }, [index, containerWidth]);

  const onLayout = (e: LayoutChangeEvent) => {
    const w = e.nativeEvent.layout.width;
    if (w && w !== containerWidth) setContainerWidth(w);
  };

  return (
    <View style={{ overflow: 'hidden' }} onLayout={onLayout}>
      <Animated.View style={{ flexDirection: 'row', width: containerWidth * React.Children.count(children), transform: [{ translateX }], opacity }}>
        {React.Children.map(children, (child, i) => (
          <View key={i} style={{ width: containerWidth }}>
            {child}
          </View>
        ))}
      </Animated.View>
    </View>
  );
}


