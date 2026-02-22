/**
 * File: src/components/SwipeableSheet.tsx
 * Purpose: Lightweight swipe-to-dismiss container for bottom sheets.
 *          Wraps sheet content with a PanResponder that listens for
 *          downward drags and calls onClose when threshold is exceeded.
 */
import React from 'react';
import { Animated, PanResponder, ViewStyle, View, GestureResponderEvent, PanResponderGestureState } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Props = {
  onClose: () => void;
  style?: ViewStyle;
  children: React.ReactNode;
};

export function SwipeableSheet({ onClose, style, children }: Props) {
  const theme = useTheme();
  const translateY = React.useRef(new Animated.Value(0)).current;

  function shouldCapture(_e: GestureResponderEvent, g: PanResponderGestureState) {
    const isVertical = Math.abs(g.dy) > Math.abs(g.dx);
    return isVertical && g.dy > 6; // downward drag
  }

  const panResponder = React.useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponder: shouldCapture,
      onMoveShouldSetPanResponderCapture: shouldCapture,
      onPanResponderMove: (_e, g) => {
        if (g.dy > 0) translateY.setValue(g.dy);
      },
      onPanResponderRelease: (_e, g) => {
        const shouldClose = g.dy > 120 || g.vy > 1.1;
        if (shouldClose) {
          Animated.timing(translateY, { toValue: 400, duration: 200, useNativeDriver: true }).start(() => {
            translateY.setValue(0);
            onClose();
          });
        } else {
          Animated.spring(translateY, { toValue: 0, bounciness: 6, useNativeDriver: true }).start();
        }
      },
    })
  ).current;

  return (
    <Animated.View
      style={[{ transform: [{ translateY }] }, style]}
      {...panResponder.panHandlers}
    >
      <View style={{ alignItems: 'center', paddingVertical: 6 }}>
        <View style={{ width: 36, height: 5, borderRadius: 3, backgroundColor: theme.colors.border }} />
      </View>
      {children}
    </Animated.View>
  );
}


