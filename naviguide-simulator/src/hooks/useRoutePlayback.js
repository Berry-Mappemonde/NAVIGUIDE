import { useCallback, useEffect, useRef, useState } from "react";
import { atlanticSpanNm } from "../engine/routePlayhead.js";
import { airHopSeconds, nmPerSecond } from "../engine/playSpeeds.js";
import { edgeAtFilmNm, filmLength } from "../engine/filmCast.js";

function playheadLength(flat) {
  return filmLength(flat) || flat?.totalNm || 0;
}

function rateAtPlayhead(flat, filmNm, sailRate, profile) {
  const edge = edgeAtFilmNm(flat, filmNm);
  if (edge?.jump) {
    const span = Math.max(1e-6, edge.filmSpan);
    return span / airHopSeconds(profile);
  }
  return sailRate;
}

export function useRoutePlayback({ flat, marks, boatKnots, enabled }) {
  const [playing, setPlaying] = useState(false);
  const [profile, setProfile] = useState("normal");
  const [nm, setNm] = useState(0);
  const [jumpToken, setJumpToken] = useState(0);
  const nmRef = useRef(0);
  const lastTs = useRef(0);
  const emitAcc = useRef(0);
  const lastAir = useRef(false);

  const totalNm = playheadLength(flat);
  const atlanticNm = atlanticSpanNm(marks, flat?.totalNm || totalNm);
  const sailRate = nmPerSecond(profile, { boatKnots, atlanticNm });

  const seek = useCallback((nextNm, { play = false, jump = false } = {}) => {
    const total = playheadLength(flat);
    const clamped = Math.max(0, Math.min(total, Number(nextNm) || 0));
    nmRef.current = clamped;
    setNm(clamped);
    if (jump) setJumpToken((n) => n + 1);
    if (play) setPlaying(true);
  }, [flat]);

  const play = useCallback(() => setPlaying(true), []);
  const pause = useCallback(() => setPlaying(false), []);
  const toggle = useCallback(() => {
    setPlaying((p) => {
      if (!p && nmRef.current >= playheadLength(flat) - 1e-6) {
        nmRef.current = 0;
        setNm(0);
      }
      return !p;
    });
  }, [flat]);

  useEffect(() => {
    if (!enabled) setPlaying(false);
  }, [enabled]);

  useEffect(() => {
    const total = playheadLength(flat);
    if (nmRef.current > total) {
      nmRef.current = total;
      setNm(total);
    }
  }, [flat]);

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
      const total = playheadLength(flat);
      const rate = rateAtPlayhead(flat, nmRef.current, sailRate, profile);
      const inAir = Boolean(edgeAtFilmNm(flat, nmRef.current)?.jump);
      if (inAir !== lastAir.current) {
        lastAir.current = inAir;
        setJumpToken((n) => n + 1);
      }
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
  }, [enabled, playing, sailRate, profile, flat]);

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
    rate: sailRate,
    sailTotalNm: flat?.totalNm || 0,
  };
}
