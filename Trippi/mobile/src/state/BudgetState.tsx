/**
 * File: src/state/BudgetState.tsx
 * Purpose: Client-side budget UI state: personal Flex Budget balance and personal
 *          transactions (deposits/withdrawals) for the Budget dashboard.
 */
import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

export type FlexTransaction = {
  id: string;
  type: 'deposit' | 'withdraw';
  amount: number;
  note?: string;
  date: string; // ISO
};

type BudgetContextValue = {
  flexBudget: number;
  transactions: FlexTransaction[];
  deposit: (amount: number, note?: string) => void;
  withdraw: (amount: number, note?: string) => void;
  reset: () => void;
};

const BudgetContext = createContext<BudgetContextValue | null>(null);

export function BudgetProvider({ children }: { children: React.ReactNode }) {
  const [flexBudget, setFlexBudget] = useState<number>(0);
  const [transactions, setTransactions] = useState<FlexTransaction[]>([]);

  const addTxn = useCallback((type: 'deposit' | 'withdraw', amount: number, note?: string) => {
    const safe = Math.max(0, amount || 0);
    const id = Math.random().toString(36).slice(2);
    const date = new Date().toISOString();
    setTransactions(prev => [{ id, type, amount: safe, note, date }, ...prev]);
    setFlexBudget(prev => (type === 'deposit' ? prev + safe : Math.max(0, prev - safe)));
  }, []);

  const deposit = useCallback((amount: number, note?: string) => addTxn('deposit', amount, note), [addTxn]);
  const withdraw = useCallback((amount: number, note?: string) => addTxn('withdraw', amount, note), [addTxn]);
  const reset = useCallback(() => { setFlexBudget(0); setTransactions([]); }, []);

  const value = useMemo(() => ({ flexBudget, transactions, deposit, withdraw, reset }), [flexBudget, transactions, deposit, withdraw, reset]);
  return <BudgetContext.Provider value={value}>{children}</BudgetContext.Provider>;
}

export function useBudget() {
  const ctx = useContext(BudgetContext);
  if (!ctx) throw new Error('useBudget must be used within BudgetProvider');
  return ctx;
}


