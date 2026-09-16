/**
 * Story of the `ici()` bag — one briefing, not four agents.
 * Tells only what is around the boat.
 */

const TERRITORY = {
  fr: {
    france_metropolitaine: "France métropolitaine",
    guyane: "Guyane",
    martinique: "Martinique",
    guadeloupe: "Guadeloupe",
    saint_barthelemy: "Saint-Barthélemy",
    saint_martin: "Saint-Martin",
    saint_pierre_et_miquelon: "Saint-Pierre-et-Miquelon",
    polynesie_francaise: "Polynésie française",
    nouvelle_caledonie: "Nouvelle-Calédonie",
    wallis_et_futuna: "Wallis-et-Futuna",
    la_reunion: "La Réunion",
    mayotte: "Mayotte",
    taaf: "Terres australes et antarctiques françaises",
  },
  en: {
    france_metropolitaine: "metropolitan France",
    guyane: "French Guiana",
    martinique: "Martinique",
    guadeloupe: "Guadeloupe",
    saint_barthelemy: "Saint Barthélemy",
    saint_martin: "Saint Martin",
    saint_pierre_et_miquelon: "Saint Pierre and Miquelon",
    polynesie_francaise: "French Polynesia",
    nouvelle_caledonie: "New Caledonia",
    wallis_et_futuna: "Wallis and Futuna",
    la_reunion: "Réunion",
    mayotte: "Mayotte",
    taaf: "French Southern and Antarctic Lands",
  },
};

function isEn(lang) {
  return lang === "en";
}

function hostOf(url) {
  if (!url || typeof url !== "string") return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function listPlaces(items, lang, max = 3) {
  const slice = (items || []).slice(0, max);
  const parts = slice.map((x) => {
    const nm = Number.isFinite(x.nm) ? ` (${x.nm} nm)` : "";
    const host = hostOf(x.url);
    return host ? `${x.name}${nm} — ${host}` : `${x.name}${nm}`;
  });
  if (!parts.length) return "";
  if (parts.length === 1) return parts[0];
  const last = parts.pop();
  return `${parts.join(", ")}${isEn(lang) ? " and " : " et "}${last}`;
}

function formatEta(hours, lang) {
  if (hours == null || !Number.isFinite(hours) || hours <= 0) return null;
  if (hours < 1) {
    const m = Math.max(1, Math.round(hours * 60));
    return isEn(lang) ? `${m} min` : `${m} min`;
  }
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (!m) return isEn(lang) ? `${h} h` : `${h} h`;
  return `${h} h ${String(m).padStart(2, "0")}`;
}

function zeeSentence(dossier, lang) {
  const en = isEn(lang);
  const zee = dossier?.zee;
  if (!zee) {
    return en
      ? "Here the boat is on the high seas — no exclusive economic zone, no port of entry to clear."
      : "Ici, le bateau est en haute mer — aucune ZEE, pas de port d’entrée à déclarer.";
  }
  if (zee.ashore || String(zee.name || "").startsWith("À terre")) {
    const extra = String(zee.name || "").startsWith("À terre")
      ? zee.name.slice("À terre".length).trim()
      : "";
    return en
      ? `Here the boat is ashore${extra ? ` ${extra}` : ""}, outside any EEZ.`
      : `Ici, le bateau est à terre${extra ? ` ${extra}` : ""}, hors ZEE.`;
  }
  if (!zee.mrgid || zee.name === "Haute mer") {
    return en
      ? "Here the boat is on the high seas — no exclusive economic zone, no port of entry to clear."
      : "Ici, le bateau est en haute mer — aucune ZEE, pas de port d’entrée à déclarer.";
  }
  const territory = TERRITORY[en ? "en" : "fr"][zee.territory];
  const where = territory
    ? (en ? `${zee.name} (${territory})` : `${zee.name} (${territory})`)
    : zee.name;
  const gold = zee.gold
    ? (en
      ? "This EEZ is Gold: formalities rest on official ports of entry."
      : "Cette ZEE est Gold : les formalités s’appuient sur des ports d’entrée officiels.")
    : (zee.territory
      ? (en
        ? "French EEZ, but Gold formalities are still incomplete in this pack."
        : "ZEE française, mais les formalités Gold sont encore incomplètes dans ce sac.")
      : (en
        ? "This is not a French Gold EEZ."
        : "Ce n’est pas une ZEE Gold française."));
  return en
    ? `Here the boat is in ${where}. ${gold}`
    : `Ici, le bateau est dans ${where}. ${gold}`;
}

function poeSentence(dossier, lang) {
  const en = isEn(lang);
  const poe = dossier?.poe || [];
  if (!poe.length) {
    if (!dossier?.zee?.mrgid) return "";
    return en
      ? "No official port of entry is listed for this EEZ in the pack."
      : "Aucun port d’entrée officiel n’est listé pour cette ZEE dans le sac.";
  }
  const listed = listPlaces(poe, lang, 4);
  return en
    ? `The nearest official ports of entry are ${listed}.`
    : `Les ports d’entrée officiels les plus proches sont ${listed}.`;
}

function ampSentence(dossier, lang) {
  const en = isEn(lang);
  const items = dossier?.amp || [];
  if (!items.length) return "";
  const listed = listPlaces(items, lang, 3);
  const first = items[0];
  const visit = hostOf(first?.visit_url);
  const manager = hostOf(first?.manager_url);
  const urls = [];
  if (visit) urls.push(en ? `visit ${visit}` : `visite ${visit}`);
  if (manager && first?.manager_url !== first?.visit_url) {
    urls.push(en ? `manager ${manager}` : `gestionnaire ${manager}`);
  }
  return en
    ? `MPAs within 30 nm: ${listed}${urls.length ? ` (${urls.join(", ")})` : ""}.`
    : `AMP dans les 30 milles : ${listed}${urls.length ? ` (${urls.join(", ")})` : ""}.`;
}

function projectsSentence(dossier, lang) {
  const listed = listPlaces(dossier?.projects, lang, 3);
  if (!listed) return "";
  return isEn(lang)
    ? `Projects within 30 nm: ${listed}.`
    : `Projets dans les 30 milles : ${listed}.`;
}

function harboursSentence(dossier, lang) {
  const en = isEn(lang);
  const bits = [];
  const marinas = listPlaces(dossier?.nearby?.marinas, lang, 3);
  if (marinas) bits.push(en ? `marinas ${marinas}` : `marinas ${marinas}`);
  const capit = listPlaces(dossier?.nearby?.capitaineries, lang, 2);
  if (capit) bits.push(en ? `harbour offices ${capit}` : `capitaineries ${capit}`);
  const wpi = listPlaces(dossier?.nearby?.wpi, lang, 2);
  if (wpi) bits.push(en ? `WPI ports ${wpi}` : `ports WPI ${wpi}`);
  if (!bits.length) return "";
  return en
    ? `Harbours within 30 nm: ${bits.join("; ")}.`
    : `Ports dans les 30 milles : ${bits.join(" ; ")}.`;
}

function scienceSentence(dossier, lang) {
  const scienceItems = (dossier?.science?.nearby || []).map((x) => ({
    ...x,
    name: x.source ? `${x.name} (${x.source})` : x.name,
  }));
  const science = listPlaces(scienceItems, lang, 3);
  if (!science) return "";
  return isEn(lang)
    ? `Science records within 30 nm: ${science}.`
    : `Dans les 30 milles : les fiches Science ${science}.`;
}

function aroundSentence(dossier, lang) {
  const en = isEn(lang);
  const bits = [
    ampSentence(dossier, lang),
    projectsSentence(dossier, lang),
    harboursSentence(dossier, lang),
    scienceSentence(dossier, lang),
    anchorageSentence(dossier, lang),
    atonSentence(dossier, lang),
  ].filter(Boolean);
  if (bits.length) return bits.join("\n\n");
  return en
    ? "Nothing notable sits inside 30 nautical miles."
    : "Rien de notable dans les 30 milles.";
}

function anchorageSentence(dossier, lang) {
  const listed = listPlaces(dossier?.nearby?.anchorages, lang, 3);
  if (!listed) return "";
  return isEn(lang)
    ? `OSM anchorages within 30 nm: ${listed}.`
    : `Mouillages OSM dans les 30 milles : ${listed}.`;
}

function atonSentence(dossier, lang) {
  const en = isEn(lang);
  const aton = dossier?.aton;
  const listed = listPlaces(aton?.nearby, lang, 3);
  if (listed) {
    const src = aton?.source || "AtoN";
    return en
      ? `Aids to navigation (${src}): ${listed}.`
      : `Balisage / AtoN (${src}) : ${listed}.`;
  }
  if (aton?.reason) {
    return en
      ? `No AtoN point in the pack (${aton.reason}).`
      : `Pas de balisage ponctuel dans le sac (${aton.reason}).`;
  }
  return "";
}

function satelliteSentence(dossier, lang) {
  const en = isEn(lang);
  const s = dossier?.satellites;
  if (!s) return "";
  const scene = s.scene || (s.scenes && s.scenes[0]);
  const derived = s.derived || {};
  const missing = Object.entries(derived)
    .filter(([, v]) => v && v.value == null)
    .map(([k, v]) => `${k}: ${v.reason || "null"}`);
  if (scene) {
    const when = scene.datetime ? String(scene.datetime).slice(0, 10) : "";
    const product = scene.product || "Sentinel";
    return en
      ? `Satellite (kind observation${when ? `, ${when}` : ""}): ${product}${scene.id ? ` ${scene.id}` : ""}${missing.length ? `; derived ${missing.join(", ")}` : ""}.`
      : `Satellite (kind observation${when ? `, ${when}` : ""}) : ${product}${scene.id ? ` ${scene.id}` : ""}${missing.length ? ` ; dérivés ${missing.join(", ")}` : ""}.`;
  }
  const reason = s.reason || "null";
  return en
    ? `Satellite (kind observation): no generated scene (${reason}).`
    : `Satellite (kind observation) : aucune scène générée (${reason}).`;
}

function weatherSentence(dossier, lang) {
  const en = isEn(lang);
  const w = dossier?.weather;
  if (!w) return "";
  const wind = w.wind;
  const wave = w.wave;
  if (!wind && !wave) {
    return en
      ? `Weather (kind forecast): empty (${w.reason || "null"}).`
      : `Météo (kind forecast) : vide (${w.reason || "null"}).`;
  }
  const bits = [];
  if (wind?.speedKnots != null) {
    bits.push(en
      ? `wind ${wind.speedKnots} kn / ${wind.dirFromDeg}°`
      : `vent ${wind.speedKnots} kn / ${wind.dirFromDeg}°`);
  }
  if (wave?.hs != null) bits.push(`Hs ${wave.hs} m`);
  if (w.current && w.current.speedKnots != null) {
    const dir = w.current.dirToDeg;
    bits.push(en
      ? `current ${w.current.speedKnots} kn / ${dir}° (RTOFS, kind forecast)`
      : `courant ${w.current.speedKnots} kn / ${dir}° (RTOFS, kind forecast)`);
  } else if (w.current == null && w.current_reason) {
    bits.push(en
      ? `current null (${w.current_reason})`
      : `courant null (${w.current_reason})`);
  }
  const model = w.model || w.source || "Open-Meteo";
  return en
    ? `Weather (kind forecast, ${model}): ${bits.join(" · ")}.`
    : `Météo (kind forecast, ${model}) : ${bits.join(" · ")}.`;
}

function emodnetSentence(dossier, lang) {
  const en = isEn(lang);
  const e = dossier?.emodnet;
  if (!e) return "";
  const bits = [];
  const depth = e.bathy?.depth_m;
  if (depth != null) bits.push(en ? `DTM ${depth} m` : `DTM ${depth} m`);
  else if (e.bathy?.reason) bits.push(`bathy null (${e.bathy.reason})`);
  if (e.seabed?.label) bits.push(en ? `seabed ${e.seabed.label}` : `fonds ${e.seabed.label}`);
  else if (e.seabed?.reason) bits.push(`fonds null (${e.seabed.reason})`);
  if (e.cables?.nearby === true) bits.push(en ? "cable nearby" : "câble au point");
  else if (e.cables?.nearby === false || e.cables?.reason) {
    bits.push(en
      ? `cables null (${e.cables.reason || "no_feature_at_point"})`
      : `câbles null (${e.cables.reason || "no_feature_at_point"})`);
  }
  if (!bits.length) {
    return en
      ? `EMODnet (kind observation): ${e.reason || "null"}.`
      : `EMODnet (kind observation) : ${e.reason || "null"}.`;
  }
  return en
    ? `EMODnet (kind observation): ${bits.join(" · ")}.`
    : `EMODnet (kind observation) : ${bits.join(" · ")}.`;
}

function reviewSentence(dossier, lang) {
  const en = isEn(lang);
  const r = dossier?.review;
  if (!r) return "";
  const bits = [];
  if (r.zee && r.zee.gold_on != null) {
    bits.push(en
      ? `EEZ Gold ${r.zee.gold_on ? "on" : "off"}`
      : `ZEE Gold ${r.zee.gold_on ? "oui" : "non"}`);
  }
  if (r.amp && r.amp.gold_on != null) {
    bits.push(en
      ? `MPA Gold ${r.amp.gold_on ? "on" : "off"}`
      : `AMP Gold ${r.amp.gold_on ? "oui" : "non"}`);
  }
  if (!bits.length) {
    if (!r.reason) return "";
    return en
      ? `Review / Gold not available (${r.reason}).`
      : `Review / Gold indisponible (${r.reason}).`;
  }
  return en
    ? `Review / Gold: ${bits.join(" · ")}.`
    : `Review / Gold : ${bits.join(" · ")}.`;
}

function signedDelta(n, unit) {
  if (!Number.isFinite(n)) return "";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n} ${unit}`;
}

export function phraseForEvent(ev, lang = "fr") {
  if (!ev) return "";
  if (ev.story?.status === "ready" && ev.story.text) return ev.story.text;
  if (typeof ev.phrase === "string" && ev.phrase.trim()) return ev.phrase;
  const en = isEn(lang);
  const p = ev.payload || {};
  const name = ev.name || p.zee?.name || p.amp?.name || p.harbour?.name;
  switch (ev.type) {
    case "zee-enter":
      return en
        ? `We have just entered ${name || "this EEZ"}.`
        : `On vient d’entrer dans ${name || "cette ZEE"}.`;
    case "zee-exit":
      return en
        ? "The boat is back on the high seas — no EEZ to clear."
        : "Retour en haute mer — plus de ZEE à déclarer.";
    case "zee-ahead": {
      const when = p.whenNm ?? ev.whenNm;
      return en
        ? `Ahead${Number.isFinite(when) ? ` in ${Math.round(when)} nm` : ""}: ${name || "another EEZ"}.`
        : `Devant${Number.isFinite(when) ? ` dans ${Math.round(when)} nm` : ""} : ${name || "une autre ZEE"}.`;
    }
    case "amp-ahead": {
      const when = p.whenNm ?? ev.whenNm;
      const visit = p.amp?.visitable || p.visitable;
      return en
        ? `MPA on the track${Number.isFinite(when) ? ` in ${Math.round(when)} nm` : ""}: ${name || "MPA"}${visit ? " (visit page in the pack)" : ""}.`
        : `AMP sur le trait${Number.isFinite(when) ? ` dans ${Math.round(when)} nm` : ""} : ${name || "AMP"}${visit ? " (page visite dans le sac)" : ""}.`;
    }
    case "poe-ahead":
      return en
        ? `Official port of entry ahead: ${p.poe?.name || name || "PoE"}${p.poe?.nm != null ? ` (${p.poe.nm} nm)` : ""}.`
        : `Port d’entrée officiel devant : ${p.poe?.name || name || "PoE"}${p.poe?.nm != null ? ` (${p.poe.nm} nm)` : ""}.`;
    case "amp-enter": {
      const visit = p.amp?.visitable || p.visitable;
      return en
        ? `A marine protected area is now inside 30 nm: ${name || "MPA"}${visit ? " (visit page in the pack)" : ""}.`
        : `Une aire marine entre dans les 30 milles : ${name || "AMP"}${visit ? " (page visite dans le sac)" : ""}.`;
    }
    case "wind-shift": {
      const kind = p.kind || ev.kind || "forecast";
      const src = p.source ? `, ${p.source}` : "";
      const delta = signedDelta(p.dTws, "kn");
      return en
        ? `Wind ${p.tws} kn / ${p.twd}° (kind: ${kind}${src})${delta ? ` — ${delta}` : ""}.`
        : `Vent ${p.tws} kn / ${p.twd}° (kind: ${kind}${src})${delta ? ` — ${delta}` : ""}.`;
    }
    case "wind-gale": {
      const kind = p.kind || ev.kind || "forecast";
      return en
        ? `Gale: ${p.tws} kn (kind: ${kind}${p.galePct != null ? `, gale ${p.galePct}%` : ""}).`
        : `Coup de vent : ${p.tws} kn (kind: ${kind}${p.galePct != null ? `, gale ${p.galePct} %` : ""}).`;
    }
    case "current-shift": {
      const kind = p.kind || ev.kind || "forecast";
      return en
        ? `Current ${p.kn} kn / ${p.dir}° (kind: ${kind}${p.source ? `, ${p.source}` : ""})${p.invert ? " — direction reversed" : ""}.`
        : `Courant ${p.kn} kn / ${p.dir}° (kind: ${kind}${p.source ? `, ${p.source}` : ""})${p.invert ? " — inversion" : ""}.`;
    }
    case "hs-shift": {
      const kind = p.kind || ev.kind || "forecast";
      return en
        ? `Significant wave ${p.hs} m (kind: ${kind}${p.alert ? ", alert" : ""}).`
        : `Houle ${p.hs} m (kind: ${kind}${p.alert ? ", alerte" : ""}).`;
    }
    case "wx-alert": {
      const bits = [];
      if (p.rainMm != null) bits.push(en ? `rain ${p.rainMm} mm/h` : `pluie ${p.rainMm} mm/h`);
      if (p.gale) bits.push(en ? "gale" : "coup de vent");
      if (p.hs != null) bits.push(`Hs ${p.hs} m`);
      const kind = p.kind || "forecast";
      return en
        ? `Weather alert (kind: ${kind}): ${bits.join(" · ") || "threshold"}.`
        : `Alerte météo (kind: ${kind}) : ${bits.join(" · ") || "seuil"}.`;
    }
    case "marina-refuge": {
      const port = p.harbour?.name || name || (en ? "a harbour" : "un port");
      const nm = p.harbour?.nm;
      const rain = p.rainMm != null ? (en ? `Rain ${p.rainMm} mm/h (GFS). ` : `Pluie ${p.rainMm} mm/h (GFS). `) : "";
      return en
        ? `${rain}Refuge: ${port}${nm != null ? ` at ${nm} nm` : ""}.`
        : `${rain}Repli : ${port}${nm != null ? ` à ${nm} nm` : ""}.`;
    }
    case "depth-alert": {
      // Skipper wording: shelf (Coastal / Cruise) or grounding (Ocean). Never "haut-fond" for a 15 m shelf.
      if (p.label && Number.isFinite(p.alertM)) {
        const head = p.label === "talonnage"
          ? (en ? "Grounding risk" : "Risque de talonner")
          : (en ? "Approaching the shelf" : "On approche du plateau");
        return en
          ? `${head}: ${p.depthM} m sounded, under ${p.alertM} m (${p.source || "DTM"}, kind: observation; not for navigation).`
          : `${head} : ${p.depthM} m sondés, sous ${p.alertM} m (${p.source || "DTM"}, kind: observation ; ne convient pas à la navigation).`;
      }
      return en
        ? `Shallow sounding ${p.depthM} m (${p.source || "DTM"}, kind: observation; not for navigation).`
        : `Haut-fond ${p.depthM} m (${p.source || "DTM"}, kind: observation ; ne convient pas à la navigation).`;
    }
    case "group": {
      if (en && ev.digest?.en) return ev.digest.en;
      if (!en && ev.digest?.fr) return ev.digest.fr;
      const members = (p.members || []).join(" + ");
      return en
        ? `Along this leg: ${members}.`
        : `Depuis cette jambe : ${members}.`;
    }
    default:
      return "";
  }
}

function eventSentence(dossier, lang) {
  const ev = dossier?.event;
  if (!ev) return "";
  return phraseForEvent(ev, lang);
}

function legSentence(dossier, lang) {
  const en = isEn(lang);
  const mark = (dossier?.marks || []).find((m) => m.kind === "leg");
  const polar = dossier?.polar || {};
  if (mark?.vehicle === "plane" || mark?.phase === "air-out" || mark?.phase === "air-return") {
    const quay = mark.from || "";
    return en
      ? `The boat stays at the dock${quay ? ` in ${quay}` : ""} during the air hop.`
      : `Le bateau reste à quai${quay ? ` à ${quay}` : ""} pendant le transfert aérien.`;
  }
  const to = mark?.to;
  const speed = Number.isFinite(polar.speedKnots) ? polar.speedKnots : null;
  const eta = formatEta(polar.etaHours, lang);
  const boat = polar.boat;
  const bits = [];
  if (to && (speed != null || eta)) {
    bits.push(en
      ? `This leg toward ${to}${speed != null ? `: ${speed} knots` : ""}${eta ? `, still ${eta} at sea` : ""}.`
      : `Cette jambe vers ${to}${speed != null ? ` : ${speed} nœuds` : ""}${eta ? `, encore ${eta} de mer` : ""}.`);
  } else if (speed != null) {
    bits.push(en ? `Boat speed on this leg: ${speed} knots.` : `Vitesse sur cette jambe : ${speed} nœuds.`);
  }
  if (boat) {
    bits.push(en ? `Polar loaded for ${boat}.` : `Polaire chargée pour ${boat}.`);
  }
  return bits.join(" ");
}

function depthSentence(dossier, lang) {
  const d = Number(dossier?.depthOffshore);
  if (!Number.isFinite(d) || Math.abs(d) < 1) return "";
  const m = Math.round(Math.abs(d));
  return isEn(lang)
    ? `GEBCO offshore sounding: ${m} m (GEBCO Compilation Group; not for navigation).`
    : `Sondage GEBCO au large : ${m} m (GEBCO Compilation Group ; ne convient pas à la navigation).`;
}

function climatologySentence(dossier, lang) {
  const en = isEn(lang);
  const c = dossier?.climatology;
  if (!c) return "";
  const month = c.month;
  const point = c.point || c;
  const w = point.wind_atlas?.most_likely || point.wind_atlas?.vector_mean;
  const wave = point.wave;
  const cur = point.current;
  const zone = c.wind;
  const src = c.source;
  if (src === "unavailable" && !w && !zone) {
    return en
      ? "The climatology atlas did not answer; the clock keeps the zone fallback (kind climatology)."
      : "L’atlas climatologie n’a pas répondu ; l’horloge garde le repli de zone (kind climatology).";
  }
  const bits = [];
  if (w) bits.push(en ? `wind ${w.speed_knots} kn / ${w.dir_deg}°` : `vent ${w.speed_knots} kn / ${w.dir_deg}°`);
  else if (zone) bits.push(en ? `zone wind ${zone.speedKnots} kn / ${zone.dirFromDeg}°` : `vent de zone ${zone.speedKnots} kn / ${zone.dirFromDeg}°`);
  if (wave?.hs_p50_m != null) bits.push(`Hs P50 ${wave.hs_p50_m} m`);
  if (wave?.hs_p90_m != null) bits.push(`Hs P90 ${wave.hs_p90_m} m`);
  if (cur && cur.speed_knots != null) {
    const dir = cur.direction_to_deg;
    bits.push(en
      ? `current ${cur.speed_knots} kn${dir != null ? ` toward ${dir}°` : ""}`
      : `courant ${cur.speed_knots} kn${dir != null ? ` vers ${dir}°` : ""}`);
  }
  const rose = c.rose || point.wind_atlas;
  if (rose?.stat === "rose" && Array.isArray(rose.directions_from) && rose.directions_from.length) {
    bits.push(en ? `8-sector rose` : `rose 8 secteurs`);
  }
  if (rose?.calm_pct != null) bits.push(en ? `calm ${rose.calm_pct}%` : `calme ${rose.calm_pct} %`);
  if (rose?.gale_pct != null) bits.push(en ? `gale ${rose.gale_pct}%` : `coup de vent ${rose.gale_pct} %`);
  const nearbyCyc = c.cyclone?.nearby ?? point.cyclone?.nearby;
  if (nearbyCyc != null) {
    bits.push(en ? `IBTrACS nearby ${nearbyCyc}` : `IBTrACS nearby ${nearbyCyc}`);
  }
  const crossings = c.crossings?.count ?? point.cyclone?.crossings_if_leg?.count;
  if (crossings != null) {
    bits.push(en ? `IBTrACS crossings on the leg: ${crossings}` : `croisements IBTrACS sur la jambe : ${crossings}`);
  }
  const period = c.period || point.period;
  const doi = c.doi?.wind || point.doi?.wind;
  const head = src === "atlas"
    ? (en
      ? `CMEMS atlas (kind climatology, month ${month}`
      : `Atlas CMEMS (kind climatology, mois ${month}`)
    : (en
      ? `Zone fallback (kind climatology, month ${month}`
      : `Repli de zone (kind climatology, mois ${month}`);
  const tail = [];
  if (period) tail.push(en ? `period ${period}` : `période ${period}`);
  if (doi) tail.push(`DOI ${doi}`);
  return `${head}${tail.length ? `, ${tail.join(", ")}` : ""})${bits.length ? ` : ${bits.join(" · ")}.` : "."}`;
}

function sourceSentence(dossier, lang) {
  const en = isEn(lang);
  const bi = dossier?.sources?.bi;
  const zee = dossier?.sources?.zee;
  const notes = [];
  if (zee === "error" && dossier?.zee?.mrgid) {
    notes.push(en
      ? "MarineRegions did not answer for the EEZ."
      : "MarineRegions n’a pas répondu pour la ZEE.");
  }
  if (bi === "unavailable") {
    notes.push(en
      ? "Blue Intelligence layers did not answer; the pack keeps the EEZ and World Port Index when they exist."
      : "Les couches Blue Intelligence n’ont pas répondu ; le sac garde la ZEE et le World Port Index quand ils existent.");
  } else if (bi === "partial") {
    notes.push(en
      ? "Some Blue Intelligence layers are missing; the pack tells only what arrived."
      : "Certaines couches Blue Intelligence manquent ; le sac ne raconte que ce qui est arrivé.");
  }
  return notes.join(" ");
}

export function narrateIci(dossier, lang = "fr") {
  if (!dossier) return "";
  const parts = [
    [zeeSentence(dossier, lang), poeSentence(dossier, lang)].filter(Boolean).join(" "),
    aroundSentence(dossier, lang),
    satelliteSentence(dossier, lang),
    weatherSentence(dossier, lang),
    emodnetSentence(dossier, lang),
    reviewSentence(dossier, lang),
    eventSentence(dossier, lang),
    depthSentence(dossier, lang),
    climatologySentence(dossier, lang),
    legSentence(dossier, lang),
    sourceSentence(dossier, lang),
  ].filter(Boolean);
  return parts.join("\n\n");
}
