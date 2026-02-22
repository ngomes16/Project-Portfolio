/**
 * File: src/components/Screen.tsx
 * Purpose: Safe-area aware screen wrapper applying consistent padding and background color.
 * Update: Adds control over safe-area `edges` so hero sections can extend to the
 *         very top when desired, and supports an optional `floatingBottom` overlay
 *         (e.g., an in-screen tab bar) that is anchored to the bottom without
 *         affecting scroll position. Also removes unnecessary extra bottom
 *         padding that previously created blank space.
 */
import React from 'react';
import { View, StyleSheet, ScrollView, ScrollViewProps } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '../theme/ThemeProvider';

type EdgeName = 'top' | 'right' | 'bottom' | 'left';
type Props = React.PropsWithChildren<{
  scroll?: boolean;
  style?: any;
  contentContainerStyle?: any;
  /** Optional safe-area edges to respect. Defaults to all edges. */
  edges?: EdgeName[];
  /** Optional floating element anchored to screen bottom (e.g., section bar). */
  floatingBottom?: React.ReactNode;
}> & Partial<ScrollViewProps>;

export function Screen({ children, style, contentContainerStyle, scroll, edges, floatingBottom, ...scrollProps }: Props) {
  const theme = useTheme();
  const edgesToUse: EdgeName[] = edges ?? ["top","left","right","bottom"];
  const includeTopPadding = edgesToUse.includes('top');
  const basePaddingTop = includeTopPadding ? theme.spacing(2) : 0;
  const basePaddingBottom = theme.spacing(2) + (floatingBottom ? 90 : 0); // leave room if floating control exists
  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.colors.background }, style]} edges={edgesToUse}>
      {scroll ? (
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={[
            styles.inner,
            {
              paddingHorizontal: theme.spacing(2),
              paddingTop: basePaddingTop,
              paddingBottom: basePaddingBottom,
            },
            contentContainerStyle,
          ]}
          {...scrollProps}
        >
          {children}
        </ScrollView>
      ) : (
        <View
          style={[
            styles.inner,
            {
              paddingHorizontal: theme.spacing(2),
              paddingTop: basePaddingTop,
              paddingBottom: basePaddingBottom,
            },
            contentContainerStyle,
          ]}
        >
          {children}
        </View>
      )}
      {floatingBottom ? (
        <View pointerEvents="box-none" style={styles.floatingContainer}>
          {floatingBottom}
        </View>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  inner: { flexGrow: 1 },
  floatingContainer: { position: 'absolute', left: 0, right: 0, bottom: 0 },
});


