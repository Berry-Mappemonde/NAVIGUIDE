import L from "leaflet";
import { circleOpts } from "./points.js";

function geometryLatLngs(geometry = {}) {
  const point = ([lon, lat]) => [lat, lon];
  const points = (coords) => (coords || [])
    .filter((coords) => Array.isArray(coords) && coords.length >= 2)
    .map(point);
  switch (geometry.type) {
    case "LineString":
      return points(geometry.coordinates);
    case "MultiLineString":
      return (geometry.coordinates || []).map(points);
    case "Polygon":
      return (geometry.coordinates || []).map(points);
    case "MultiPolygon":
      return (geometry.coordinates || []).map((polygon) => polygon.map(points));
    default:
      return null;
  }
}

function isPolygon(type) {
  return type === "Polygon" || type === "MultiPolygon";
}

function isCluster(feature) {
  return Number(feature?.properties?.clusterCount) > 1;
}

/**
 * Groupe durable pour un catalogue : un pan ne recrée que les features
 * entrées/sorties du viewport, les objets encore visibles sont patchés.
 */
export class SpatialCatalogLayer {
  constructor(map, {
    color,
    kind,
    pane,
    pointFillOpacity,
    styleFor,
    onFeature,
  } = {}) {
    this.map = map;
    this.group = L.layerGroup().addTo(map);
    this.renderer = L.canvas({ padding: 0.5, tolerance: 8 });
    this.records = new Map();
    this.configure({ color, kind, pane, pointFillOpacity, styleFor, onFeature });
  }

  configure({ color, kind, pane, pointFillOpacity, styleFor, onFeature } = {}) {
    this.color = color || this.color || "#38bdf8";
    this.kind = kind || this.kind || "catalog";
    this.pane = pane || this.pane;
    this.pointFillOpacity = pointFillOpacity ?? this.pointFillOpacity ?? 0.8;
    this.styleFor = styleFor || this.styleFor;
    this.onFeature = onFeature || this.onFeature;
  }

  _featureKey(feature, index) {
    return String(feature?.properties?.naviguideCatalogId || `${this.kind}:${index}`);
  }

  _pointOptions(feature) {
    const clusterCount = Number(feature?.properties?.clusterCount) || 1;
    return circleOpts(this.color, {
      zoom: this.map.getZoom(),
      bump: clusterCount > 1 ? Math.min(6, Math.log2(clusterCount)) : 0,
      fillOpacity: this.pointFillOpacity,
      renderer: this.renderer,
      ...(this.pane ? { pane: this.pane } : {}),
    });
  }

  _shapeOptions(feature) {
    const style = this.styleFor?.(feature?.properties || {}) || {};
    return {
      color: this.color,
      weight: 2.5,
      opacity: 0.85,
      fillOpacity: isPolygon(feature?.geometry?.type) ? 0.12 : 0,
      ...(this.pane ? { pane: this.pane } : {}),
      ...style,
    };
  }

  _bindClick(layer, feature) {
    layer.on("click", (event) => {
      L.DomEvent.stopPropagation(event);
      const [lon, lat] = (feature?.geometry?.coordinates || []);
      if (isCluster(feature)) {
        this.map.setView(
          event.latlng || [lat, lon],
          Math.min(this.map.getMaxZoom(), this.map.getZoom() + 2),
          { animate: true },
        );
        return;
      }
      const location = event.latlng || { lat, lng: lon };
      this.onFeature?.({
        lon: location.lng,
        lat: location.lat,
        kind: this.kind,
        props: feature.properties || {},
      });
    });
  }

  _create(feature) {
    const geometry = feature?.geometry || {};
    let layer = null;
    if (geometry.type === "Point") {
      const [lon, lat] = geometry.coordinates || [];
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
      layer = L.circleMarker([lat, lon], this._pointOptions(feature));
    } else {
      const latlngs = geometryLatLngs(geometry);
      if (!latlngs) return null;
      layer = isPolygon(geometry.type)
        ? L.polygon(latlngs, this._shapeOptions(feature))
        : L.polyline(latlngs, this._shapeOptions(feature));
    }
    this._bindClick(layer, feature);
    this.group.addLayer(layer);
    return { layer, type: geometry.type, feature };
  }

  _update(record, feature) {
    const geometry = feature?.geometry || {};
    if (record.type !== geometry.type) {
      this.group.removeLayer(record.layer);
      return this._create(feature);
    }
    if (geometry.type === "Point") {
      const [lon, lat] = geometry.coordinates || [];
      record.layer.setLatLng([lat, lon]);
      record.layer.setStyle(this._pointOptions(feature));
    } else {
      const latlngs = geometryLatLngs(geometry);
      if (!latlngs) return null;
      record.layer.setLatLngs(latlngs);
      record.layer.setStyle(this._shapeOptions(feature));
    }
    record.feature = feature;
    return record;
  }

  update(featureCollection) {
    const next = new Map();
    (featureCollection?.features || []).forEach((feature, index) => {
      const key = this._featureKey(feature, index);
      const existing = this.records.get(key);
      const record = existing ? this._update(existing, feature) : this._create(feature);
      if (record) next.set(key, record);
    });
    this.records.forEach((record, key) => {
      if (!next.has(key)) this.group.removeLayer(record.layer);
    });
    this.records = next;
  }

  remove() {
    this.group.remove();
    this.records.clear();
  }
}
