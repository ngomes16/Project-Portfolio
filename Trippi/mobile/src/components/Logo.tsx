/**
 * File: src/components/Logo.tsx
 * Purpose: Reusable logo component to display the Trippi logo with optional sizing.
 */
import React from 'react';
import { Image, ImageProps, StyleSheet } from 'react-native';

type Props = {
  size?: number;
} & Partial<ImageProps>;

export function Logo({ size = 72, style, ...rest }: Props) {
  return (
    <Image
      source={require('../../assets/Trippi_logo.png')}
      style={[styles.image, { width: size, height: size }, style]}
      resizeMode="contain"
      {...rest}
    />
  );
}

const styles = StyleSheet.create({
  image: {
    alignSelf: 'center',
  },
});


