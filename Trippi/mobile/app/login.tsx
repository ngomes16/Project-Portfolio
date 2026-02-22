/**
 * File: app/login.tsx
 * Purpose: Modern login UI. On submit, routes to the main tabs. Uses
 *          `PasswordRequirement` component for signup hints. Adds inline
 *          error messaging and loading indicators for better UX.
 * Update: On signup, writes user profile to Firestore with server timestamps
 *         via `upsertUserProfile` service.
 */
import React from 'react';
import { View, Text, StyleSheet, KeyboardAvoidingView, Platform, TextInput, ScrollView, ActivityIndicator } from 'react-native';
import { Screen } from '../src/components/Screen';
import { Logo } from '../src/components/Logo';
import { TextField } from '../src/components/TextField';
import { Button } from '../src/components/Button';
import { useTheme } from '../src/theme/ThemeProvider';
import { useRouter } from 'expo-router';
import { useAuth } from '../src/state/AuthContext';

import { createUserWithEmailAndPassword, signInWithEmailAndPassword } from 'firebase/auth';
import { auth } from '../src/firebase';
import { upsertUserProfile } from '../src/services/firestore';
import { Segmented } from '../src/components/Segmented';
import { PasswordRequirement } from '../src/components/login/PasswordRequirement';
import { KeyboardAccessory } from '../src/components/KeyboardAccessory';

type Mode = 'login' | 'signup';

export default function LoginScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { loading: authLoading } = useAuth();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [displayName, setDisplayName] = React.useState('');
  const [mode, setMode] = React.useState<Mode>('login');
  const [submitting, setSubmitting] = React.useState(false);
  const [errorText, setErrorText] = React.useState<string>('');

  const [passwordRequirements, setPasswordRequirements] = React.useState({
    length: false,
    letter: false,
    number: false,
    special: false,
  });

  const isPasswordValid = Object.values(passwordRequirements).every(Boolean);

  const displayNameRef = React.useRef<TextInput>(null);
  const emailRef = React.useRef<TextInput>(null);
  const passwordRef = React.useRef<TextInput>(null);
  const accessoryId = 'loginAccessory';

  function focusPrev() {
    if (mode === 'signup') {
      if (passwordRef.current?.isFocused()) emailRef.current?.focus();
      else if (emailRef.current?.isFocused()) displayNameRef.current?.focus();
    } else {
      if (passwordRef.current?.isFocused()) emailRef.current?.focus();
    }
  }

  function focusNext() {
    if (mode === 'signup') {
      if (displayNameRef.current?.isFocused()) emailRef.current?.focus();
      else if (emailRef.current?.isFocused()) passwordRef.current?.focus();
    } else {
      if (emailRef.current?.isFocused()) passwordRef.current?.focus();
    }
  }

  const validatePassword = (text: string) => {
    setPassword(text);
    setPasswordRequirements({
      length: text.length > 6,
      letter: /[a-zA-Z]/.test(text),
      number: /\d/.test(text),
      special: /[^a-zA-Z0-9]/.test(text),
    });
  };

  const handleLogin = async () => {
    setSubmitting(true);
    setErrorText('');
    try {
      await signInWithEmailAndPassword(auth as any, email, password);
      // AuthContext redirects on success
    } catch (error: any) {
      if (error?.code === 'auth/invalid-credential') {
        setErrorText('Email or password is incorrect.');
      } else if (error?.code === 'auth/network-request-failed') {
        setErrorText('Network error. Check your connection and try again.');
      } else {
        setErrorText(error?.message || 'Login failed.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignUp = async () => {
    if (!isPasswordValid) {
      setErrorText('Please ensure your password meets all requirements.');
      return;
    }
    setSubmitting(true);
    setErrorText('');
    try {
      const userCredential = await createUserWithEmailAndPassword(auth as any, email, password);
      const user = userCredential.user;
      await upsertUserProfile({ uid: user.uid, email: user.email, displayName, photoURL: user.photoURL });

      // AuthContext redirects on success
    } catch (error: any) {
      if (error?.code === 'auth/email-already-in-use') {
        setErrorText('This email is already in use. Try logging in instead.');
      } else if (error?.code === 'auth/weak-password') {
        setErrorText('Password is too weak. Please strengthen it.');
      } else {
        setErrorText(error?.message || 'Sign up failed.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'center' }}>
          <View style={{ alignItems: 'center' }}>
            <Logo size={84} />
            <Text style={{ color: theme.colors.textPrimary, fontSize: 24, fontWeight: '800', marginTop: 12 }}>
              {mode === 'login' ? 'Welcome to Trippi' : 'Create your Account'}
            </Text>
            <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Plan together. Save smarter.</Text>
          </View>

          <View style={{ marginTop: theme.spacing(4), paddingHorizontal: theme.spacing(2) }}>
            {(authLoading || submitting) && (
              <View style={{ alignItems: 'center', marginBottom: theme.spacing(2) }}>
                <ActivityIndicator color={theme.colors.primary} />
              </View>
            )}
            {!!errorText && (
              <View style={{ backgroundColor: '#3B1F2B', borderColor: '#7C5CFF', borderWidth: 0, padding: 8, borderRadius: theme.radius.sm, marginBottom: theme.spacing(1) }}>
                <Text style={{ color: '#FFA5B0' }}>{errorText}</Text>
              </View>
            )}
            <Segmented
              options={[{ label: 'Login', value: 'login' }, { label: 'Sign Up', value: 'signup' }]}
              value={mode}
              onChange={(val) => setMode(val as Mode)}
              style={{ marginBottom: theme.spacing(2) }}
            />
            {mode === 'signup' && (
              <TextField
                ref={displayNameRef}
                label="Display Name"
                placeholder="Your Name"
                value={displayName}
                onChangeText={setDisplayName}
                returnKeyType="next"
                onSubmitEditing={() => emailRef.current?.focus()}
                blurOnSubmit={false}
                inputAccessoryViewID={accessoryId}
              />
            )}
            <TextField
              ref={emailRef}
              label="Email"
              placeholder="you@example.com"
              autoCapitalize="none"
              keyboardType="email-address"
              value={email}
              onChangeText={setEmail}
              returnKeyType="next"
              onSubmitEditing={() => passwordRef.current?.focus()}
              blurOnSubmit={false}
              inputAccessoryViewID={accessoryId}
            />
            <TextField
              ref={passwordRef}
              label="Password"
              placeholder="Your password"
              secureTextEntry
              value={password}
              onChangeText={mode === 'signup' ? validatePassword : setPassword}
              returnKeyType="done"
              onSubmitEditing={mode === 'login' ? handleLogin : handleSignUp}
              inputAccessoryViewID={accessoryId}
            />
            
            {mode === 'signup' && (
              <View style={{ marginTop: theme.spacing(1), marginBottom: theme.spacing(1), paddingHorizontal: theme.spacing(1) }}>
                <PasswordRequirement met={passwordRequirements.length} label="Over 6 characters long" />
                <PasswordRequirement met={passwordRequirements.letter} label="Contains a letter" />
                <PasswordRequirement met={passwordRequirements.number} label="Contains a number" />
                <PasswordRequirement met={passwordRequirements.special} label="Contains a special character" />
              </View>
            )}

            <Button
              label={mode === 'login' ? 'Log in' : 'Create Account'}
              onPress={mode === 'login' ? handleLogin : handleSignUp}
              style={{ marginTop: 8 }}
              disabled={(mode === 'signup' && !isPasswordValid) || submitting || authLoading}
            />
                        {/* <Button label="Continue as Guest" variant="secondary" onPress={() => router.replace('/(tabs)')} style={{ marginTop: 8 }} /> */}
          </View>
        </ScrollView>
        <KeyboardAccessory id={accessoryId} onPrev={focusPrev} onNext={focusNext} onDone={() => {}} />
      </KeyboardAvoidingView>
    </Screen>
  );
}


