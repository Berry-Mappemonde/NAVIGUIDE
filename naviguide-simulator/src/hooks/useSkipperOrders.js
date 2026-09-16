import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_PROFILE,
  PROFILES,
  clearSavedOrders,
  ordersLine,
  readSavedOrders,
  resolveOrders,
  writeSavedOrders,
} from "../engine/skipperOrders.js";

const NOTICE_MS = 6000;

function storage() {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

function suggestKey(orders) {
  if (!orders?.suggest) return null;
  return `${orders.boat?.expeditionId || orders.boat?.name || "polar"}:${orders.suggest.profile}`;
}

/**
 * Skipper orders: one character, saved in this tab (localStorage, profile only).
 * Never awaits a model. Never rewinds the film. Cinema keeps the orders active.
 * A small polar proposes Coastal; it never switches silently.
 */
export function useSkipperOrders({ polar = null, mode = "simulation", lang = "fr" } = {}) {
  const [profile, setProfileState] = useState(
    () => readSavedOrders(storage())?.profile ?? DEFAULT_PROFILE,
  );
  const [notice, setNotice] = useState(null);
  const [dismissed, setDismissed] = useState(null);
  const timerRef = useRef(null);
  const firstRef = useRef(true);

  const orders = useMemo(
    () => resolveOrders({ profile }, { polar, mode }),
    [profile, polar, mode],
  );

  useEffect(() => {
    if (firstRef.current) {
      firstRef.current = false;
      return undefined;
    }
    setNotice(ordersLine(orders, lang));
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setNotice(null), NOTICE_MS);
    return () => clearTimeout(timerRef.current);
    // One cyan line per character change only — not on polar / mode / lang changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  const setProfile = useCallback((next) => {
    if (!PROFILES.includes(next)) return;
    setProfileState((prev) => {
      if (prev === next) return prev;
      writeSavedOrders(storage(), { profile: next });
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    clearSavedOrders(storage());
    setProfileState(DEFAULT_PROFILE);
  }, []);

  const key = suggestKey(orders);
  const suggest = orders.suggest && dismissed !== key ? orders.suggest : null;
  const acceptSuggest = useCallback(() => {
    if (orders.suggest) setProfile(orders.suggest.profile);
  }, [orders.suggest, setProfile]);
  const dismissSuggest = useCallback(() => setDismissed(key), [key]);

  return {
    orders,
    profile,
    setProfile,
    reset,
    notice,
    suggest,
    acceptSuggest,
    dismissSuggest,
  };
}
