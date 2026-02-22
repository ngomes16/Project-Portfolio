/**
 * File: src/components/PieChartWithOverlay.tsx
 * Purpose: Reusable pie chart with interactive overlay tooltip for Home tab and others.
 *          Wraps SavingsPieChart and handles hit-testing and tooltip positioning.
 */
import React from 'react';
import { Animated, Dimensions, Modal, Pressable, View } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { SavingsPieChart } from './SavingsPieChart';

export function PieChartWithOverlay({ size, thickness, data, frameWidth }: { size: number; thickness: number; data: { name: string; saved: number; goal: number; color: string }[]; frameWidth: number }) {
  const center = size / 2;
  const totalGoal = Math.max(1, data.reduce((s, t) => s + Math.max(0, t.goal), 0));
  const radius = (size - thickness) / 2;
  const inner = radius - thickness / 2 - 4;
  const outer = radius + thickness / 2 + 4;
  const [selectedIdx, setSelectedIdx] = React.useState<number | null>(null);
  const [anchor, setAnchor] = React.useState<{ x: number; y: number } | null>(null);
  const fade = React.useRef(new Animated.Value(0)).current;
  const containerRef = React.useRef<any>(null);
  const [containerWin, setContainerWin] = React.useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const theme = useTheme();
  const overlayLeft = frameWidth ? (frameWidth - size) / 2 : 0;

  React.useEffect(() => {
    if (selectedIdx !== null && containerRef.current?.measureInWindow) {
      containerRef.current.measureInWindow((x: number, y: number, width: number, height: number) => {
        setContainerWin({ x, y, width, height });
      });
    }
  }, [selectedIdx]);

  const getSliceIndexFromPoint = (x: number, y: number) => {
    const dx = x - center;
    const dy = y - center;
    const r = Math.sqrt(dx * dx + dy * dy);
    if (r < inner || r > outer) return -1; // outside ring
    let angle = Math.atan2(dy, dx) * (180 / Math.PI);
    angle = (angle + 360) % 360;
    const frac = ((angle + 90) % 360) / 360;
    let acc = 0;
    for (let i = 0; i < data.length; i++) {
      const seg = Math.max(0, data[i].goal) / totalGoal;
      if (frac >= acc && frac < acc + seg) return i;
      acc += seg;
    }
    return data.length - 1;
  };

  const getAnchorForSlice = (idx: number) => {
    let acc = 0;
    for (let i = 0; i < idx; i++) acc += Math.max(0, data[i].goal) / totalGoal;
    const seg = Math.max(0, data[idx].goal) / totalGoal;
    const mid = acc + seg / 2;
    const angleDeg = (mid * 360 + 270) % 360;
    const rad = (angleDeg * Math.PI) / 180;
    const r = radius + thickness + 60;
    const x = center + Math.cos(rad) * r;
    const y = center + Math.sin(rad) * r;
    return { x, y };
  };

  return (
    <View ref={containerRef} style={{ width: frameWidth || size, height: size, position: 'relative', alignItems: 'center', justifyContent: 'center', overflow: 'visible' }}>
      <SavingsPieChart size={size} thickness={thickness} slices={data.map(t => ({ saved: t.saved, goal: t.goal, color: t.color }))} />
      <Pressable
        style={{ position: 'absolute', top: 0, left: (frameWidth ? (frameWidth - size) / 2 : 0), width: size, height: size }}
        onPress={(e) => {
          const { locationX, locationY } = (e.nativeEvent as any);
          const idx = getSliceIndexFromPoint(locationX, locationY);
          if (idx >= 0) {
            const pos = getAnchorForSlice(idx);
            setSelectedIdx(idx);
            setAnchor(pos);
            fade.setValue(0);
            Animated.timing(fade, { toValue: 1, duration: 120, useNativeDriver: true }).start();
          } else {
            setSelectedIdx(null);
          }
        }}
      />
      {selectedIdx !== null && anchor && (
        <Modal transparent visible onRequestClose={() => setSelectedIdx(null)}>
          <View style={{ flex: 1 }}>
            <Pressable style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0, zIndex: 0 }} onPress={() => setSelectedIdx(null)} />
            {containerWin && (
              <Pressable
                style={{ position: 'absolute', zIndex: 1, left: (containerWin.x || 0) + overlayLeft, top: (containerWin.y || 0), width: size, height: size }}
                onPress={(e) => {
                  const { locationX, locationY } = (e.nativeEvent as any);
                  const idx = getSliceIndexFromPoint(locationX, locationY);
                  if (idx >= 0) {
                    const pos = getAnchorForSlice(idx);
                    setSelectedIdx(idx);
                    setAnchor(pos);
                    fade.setValue(0);
                    Animated.timing(fade, { toValue: 1, duration: 120, useNativeDriver: true }).start();
                  } else {
                    setSelectedIdx(null);
                  }
                }}
              />
            )}
            {(() => {
              const win = Dimensions.get('window');
              const width = 220; const height = 56; const pad = 8; const gap = 12;
              const isLeftSide = anchor.x < center;
              let left = (containerWin?.x || 0) + overlayLeft + anchor.x + (isLeftSide ? -(gap + width) : gap);
              let top = (containerWin?.y || 0) + anchor.y - height / 2;
              left = Math.max(pad, Math.min(win.width - width - pad, left));
              top = Math.max(pad, Math.min(win.height - height - pad, top));
              return (
                <Animated.View style={{ position: 'absolute', zIndex: 2, left, top, opacity: fade, transform: [{ translateY: fade.interpolate({ inputRange: [0,1], outputRange: [6,0] }) }], backgroundColor: theme.colors.surface, padding: 10, borderRadius: 10, borderColor: theme.colors.border, borderWidth: 1, minWidth: width, shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 8, elevation: 4 }}>
                  <TextBlock title={data[selectedIdx].name} saved={data[selectedIdx].saved} goal={data[selectedIdx].goal} />
                </Animated.View>
              );
            })()}
          </View>
        </Modal>
      )}
    </View>
  );
}

function TextBlock({ title, saved, goal }: { title: string; saved: number; goal: number }) {
  const theme = useTheme();
  return (
    <View>
      <Animated.Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{title}</Animated.Text>
      <Animated.Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>${saved} / ${goal}</Animated.Text>
    </View>
  );
}


