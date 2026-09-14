export const BI_COLORS = {
  biProjects: "#06b6d4",
  biMarinas: "#ef4444",
  biCapitaineries: "#7dd3fc",
  biPoe: "#d97706",
  biAmp: "#22c55e",
};

export const EMODNET_WMS = [
  {
    key: "wmsBathy",
    url: "https://ows.emodnet-bathymetry.eu/wms",
    layers: "mean_multicolour",
    pane: "sim-wms-bathy",
    zIndex: 240,
    opacity: 0.5,
    attribution: "EMODnet Bathymetry",
  },
  {
    key: "wmsSubstrate",
    url: "https://drive.emodnet-geology.eu/geoserver/gtk/wms",
    layers: "seabed_substrate_1m",
    pane: "sim-wms-substrate",
    zIndex: 310,
    opacity: 0.75,
    attribution: "EMODnet Geology",
  },
  {
    key: "wmsCables",
    url: "https://ows.emodnet-humanactivities.eu/wms",
    layers: "telecablesactual,powercables",
    pane: "sim-wms-cables",
    zIndex: 370,
    opacity: 1,
    attribution: "EMODnet Human Activities",
  },
];

export const ALL_LAYER_CONFIG = [
  { key: "zee", labelKey: "layerZee", titleKey: "layerZeeTitle", color: "#0e7490", showKey: "showZee", toggleKey: "setShowZee", loadingKey: "loadingZee", errorKey: "errorZee" },
  { key: "wpi", labelKey: "layerPorts", titleKey: "layerPortsTitle", color: "#f59e0b", showKey: "showPorts", toggleKey: "setShowPorts", loadingKey: "loadingPorts", errorKey: "errorPorts" },
  { key: "balisage", labelKey: "layerBalisage", titleKey: "layerBalisageTitle", color: "#10b981", showKey: "showBalisage", toggleKey: "setShowBalisage", loadingKey: "loadingBalisage", errorKey: "errorBalisage" },
  { key: "projects", labelKey: "layerBiProjects", titleKey: "layerBiProjectsTitle", color: BI_COLORS.biProjects, showKey: "showBiProjects", toggleKey: "setShowBiProjects", loadingKey: "loadingBiProjects", errorKey: "errorBiProjects" },
  { key: "marinas", labelKey: "layerBiMarinas", titleKey: "layerBiMarinasTitle", color: BI_COLORS.biMarinas, showKey: "showBiMarinas", toggleKey: "setShowBiMarinas", loadingKey: "loadingBiMarinas", errorKey: "errorBiMarinas" },
  { key: "capitaineries", labelKey: "layerBiCapitaineries", titleKey: "layerBiCapitaineriesTitle", color: BI_COLORS.biCapitaineries, showKey: "showBiCapitaineries", toggleKey: "setShowBiCapitaineries", loadingKey: "loadingBiCapitaineries", errorKey: "errorBiCapitaineries" },
  { key: "poe", labelKey: "layerBiPoe", titleKey: "layerBiPoeTitle", color: BI_COLORS.biPoe, showKey: "showBiPoe", toggleKey: "setShowBiPoe", loadingKey: "loadingBiPoe", errorKey: "errorBiPoe" },
  { key: "amp", labelKey: "layerBiAmp", titleKey: "layerBiAmpTitle", color: BI_COLORS.biAmp, showKey: "showBiAmp", toggleKey: "setShowBiAmp", loadingKey: "loadingBiAmp", errorKey: "errorBiAmp" },
  { key: "science", labelKey: "layerScience", titleKey: "layerScienceTitle", color: "#a78bfa", showKey: "showScience", toggleKey: "setShowScience", loadingKey: "loadingScience", errorKey: "errorScience" },
  { key: "climatology", labelKey: "layerClimatology", titleKey: "layerClimatologyTitle", color: "#38bdf8", showKey: "showClimatology", toggleKey: "setShowClimatology", loadingKey: "loadingClimatology", errorKey: "errorClimatology" },
  { key: "wmsBathy", labelKey: "layerWmsBathy", titleKey: "layerWmsBathyTitle", color: "#0ea5e9", showKey: "showWmsBathy", toggleKey: "setShowWmsBathy", loadingKey: "loadingWmsBathy", errorKey: "errorWmsBathy" },
  { key: "wmsSubstrate", labelKey: "layerWmsSubstrate", titleKey: "layerWmsSubstrateTitle", color: "#a16207", showKey: "showWmsSubstrate", toggleKey: "setShowWmsSubstrate", loadingKey: "loadingWmsSubstrate", errorKey: "errorWmsSubstrate" },
  { key: "wmsCables", labelKey: "layerWmsCables", titleKey: "layerWmsCablesTitle", color: "#e11d48", showKey: "showWmsCables", toggleKey: "setShowWmsCables", loadingKey: "loadingWmsCables", errorKey: "errorWmsCables" },
];
