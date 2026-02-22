/**
 * File: app/ai.tsx
 * Purpose: Dedicated AI Trip Planner screen showcasing a colorful, engaging sample conversation that produces a detailed 4-day Chicago itinerary.
 * Update: Fix expo-router Link href to a valid route. Changed back link to '/(tabs)'.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../src/components/Screen';
import { useTheme } from '../src/theme/ThemeProvider';
import { ChatBubble } from '../src/components/chat/ChatBubble';
import { Link } from 'expo-router';

export default function AIScreen() {
  const theme = useTheme();
  return (
    <Screen scroll>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
        <Link href="/(tabs)" asChild>
          <Text style={{ color: theme.colors.primary }}>{'< Back to Home'}</Text>
        </Link>
      </View>
      <Text style={[styles.title, { color: theme.colors.textPrimary }]}>AI Trip Planner</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Sample conversation</Text>

      <View style={{ marginTop: 12 }} />
      <ChatBubble from="user" text="Plan a fun 4-day trip to Chicago for 4 friends. Keep it walkable and budget-friendly." />
      <ChatBubble from="ai" text="Great! I’ll propose a balanced plan with iconic sights, food, and evening vibes. What’s your budget target and travel dates?" />
      <ChatBubble from="user" text="Around $4,000 total. Sept 20-24." />
      <ChatBubble from="ai" text="Perfect. I’ll fit lodging in the Loop, transit passes, museum time, and a classic river cruise." />

      <ChatBubble from="ai" text={
        'Day 1 (Sat)\n• Morning: Arrive ORD → CTA Blue Line to Loop\n• Afternoon: Check-in (Loop hotel), Millennium Park & The Bean\n• Evening: Deep-dish welcome dinner, Riverwalk stroll' } />
      <ChatBubble from="ai" text={
        'Day 2 (Sun)\n• Morning: Art Institute (fast pass)\n• Afternoon: West Loop bites (casual), coffee crawl\n• Evening: Architecture Boat Tour at sunset' } />
      <ChatBubble from="ai" text={
        'Day 3 (Mon)\n• Morning: Museum of Science & Industry\n• Afternoon: Magnificent Mile shopping windows\n• Evening: Green Mill jazz club (table for 4)' } />
      <ChatBubble from="ai" text={
        'Day 4 (Tue)\n• Morning: Brunch in River North\n• Afternoon: Riverwalk or last photo spots\n• Late afternoon: CTA to ORD and depart' } />

      <ChatBubble from="user" text="Looks great! Add budget line items?" />
      <ChatBubble from="ai" text={
        'Lodging $1500, Flights $1200, CTA Passes $60, Art Institute $120, Boat Tour $200, Museum of Science $160, Food/Drinks ~$580. Total ≈ $3820.' } />
      <ChatBubble from="user" text="Add to my itinerary and split costs evenly." />
      <ChatBubble from="ai" text="Done. I added items with per-person estimates and even split. Want me to invite friends next?" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '700' },
});


