import { useCallback, useEffect, useRef, useState } from "react";
import { atlanticSpanNm } from "../engine/routePlayhead.js";
import { nmPerSecond } from "../engine/playSpeeds.js";

export function useRoutePlayback({ flat, marks, boatKnots, enabled }) {
  const [playing, setPlaying] = useState(false);
  const [profile, setProfile] = useState("normal");
  const [nm, setNm] = useState(0);
  const [jumpToken, setJumpToken] = useState(0);
  const nmRef = useRef(0);
  const lastTs = useRef(0);
  const emitAcc = useRef(0);

  const totalNm = flat?.totalNm || 0;
  const atlanticNm = atlanticSpanNm(marks, totalNm);
  const rate = nmPerSecond(profile, { boatKnots, atlanticNm });

  const seek = useCallback((nextNm, { play = false, jump = false } = {}) => {
    const total = flat?.totalNm || 0;
    const clamped = Math.max(0, Math.min(total, Number(nextNm) || 0));
    nmRef.current = clamped;
    setNm(clamped);
    if (jump) setJumpToken((n) => n + 1);
    if (play) setPlaying(true);
  }, [flat?.totalNm]);

  const play = useCallback(() => setPlaying(true), []);
  const pause = useCallback(() => setPlaying(false), []);
  const toggle = useCallback(() => {
    setPlaying((p) => {
      if (!p && nmRef.current >= (flat?.totalNm || 0) - 1e-6) {
        nmRef.current = 0;
        setNm(0);
      }
      return !p;
    });
  }, [flat?.totalNm]);

  useEffect(() => {
    if (!enabled) setPlaying(false);
  }, [enabled]);

  useEffect(() => {
    const total = flat?.totalNm || 0;
    if (nmRef.current > total) {
      nmRef.current = total;
      setNm(total);
    }
  }, [flat?.totalNm]);

  useEffect(() => {
    if (!enabled || !playing) {
      lastTs.current = 0;
      return undefined;
    }
    let raf = 0;
    const loop = (ts) => {
      if (!lastTs.current) lastTs.current = ts;
      const dt = Math.min(0.08, (ts - lastTs.current) / 1000);
      lastTs.current = ts;
      const total = flat?.totalNm || 0;
      const next = Math.min(total, nmRef.current + rate * dt);
      nmRef.current = next;
      emitAcc.current += dt;
      if (emitAcc.current >= 1 / 12 || next >= total) {
        emitAcc.current = 0;
        setNm(next);
      }
      if (next >= total) {
        setPlaying(false);
        setNm(total);
        return;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [enabled, playing, rate, flat?.totalNm]);

  return {
    nm,
    playing,
    profile,
    setProfile,
    play,
    pause,
    toggle,
    seek,
    jumpToken,
    atlanticNm,
    totalNm,
    rate,
  };
}
