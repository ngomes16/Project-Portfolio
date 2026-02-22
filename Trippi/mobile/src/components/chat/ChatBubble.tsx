/**
 * File: src/components/chat/ChatBubble.tsx
 * Purpose: Reusable chat bubble for AI/User messages with modern styling.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';

type Props = { from: 'ai' | 'user'; text: string };

export function ChatBubble({ from, text }: Props) {
  const theme = useTheme();
  const isUser = from === 'user';
  return (
    <View style={{
      alignSelf: isUser ? 'flex-end' : 'flex-start',
      maxWidth: '85%',
      backgroundColor: isUser ? theme.colors.primary : theme.colors.surface,
      padding: 12,
      borderRadius: 14,
      borderTopRightRadius: isUser ? 4 : 14,
      borderTopLeftRadius: isUser ? 14 : 4,
      marginTop: 10,
    }}>
      <Text style={{ color: isUser ? '#ffffff' : theme.colors.textPrimary }}>{text}</Text>
    </View>
  );
}


