export const LEAFLET_BUILTIN_PANES = {
  tilePane: 200,
  overlayPane: 400,
  shadowPane: 500,
  markerPane: 600,
  tooltipPane: 650,
  popupPane: 700,
};

export const PANES = [
  { name: "zee-wms", zIndex: 250 },
  { name: "balisage", zIndex: 260 },
  { name: "route", zIndex: 380 },
  { name: "amp", zIndex: 420 },
  { name: "boat", zIndex: 620 },
];

export function createPanes(map) {
  PANES.forEach(({ name, zIndex }) => {
    map.createPane(name);
    map.getPane(name).style.zIndex = String(zIndex);
  });
}

export function paneOrder() {
  return PANES.map((p) => p.name);
}
