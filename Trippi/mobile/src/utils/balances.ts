/**
 * File: src/utils/balances.ts
 * Purpose: Compute per-member balances from expenses and contributions.
 */
import { Trip } from '../data/sample';

export type MemberBalance = { memberId: string; name: string; balance: number };

export function computeBalances(trip: Trip): MemberBalance[] {
  const memberMap = new Map(trip.members.map(m => [m.id, m.name] as const));
  const balances = new Map<string, number>();
  for (const m of trip.members) balances.set(m.id, 0);

  for (const exp of trip.expenses || []) {
    const shares = exp.splitWith.length > 0 ? exp.amount / exp.splitWith.length : 0;
    // Each participant owes their share
    for (const id of exp.splitWith) {
      balances.set(id, (balances.get(id) || 0) - shares);
    }
    // Payer paid the whole amount
    balances.set(exp.paidBy, (balances.get(exp.paidBy) || 0) + exp.amount);
  }

  for (const c of trip.contributions || []) {
    balances.set(c.memberId, (balances.get(c.memberId) || 0) + c.amount);
  }

  const result: MemberBalance[] = [];
  balances.forEach((balance, memberId) => {
    result.push({ memberId, name: memberMap.get(memberId) || 'Unknown', balance });
  });
  // Sort receivers first (positive), then by amount desc
  return result.sort((a, b) => b.balance - a.balance);
}


