export function getDemoSteps(lang = "en", replayReady = false) {
  const fr = lang === "fr";
  return [
    {
      id: "welcome",
      action: "welcome",
      title: fr ? "Visite guidée de NAVIGUIDE" : "NAVIGUIDE guided tour",
      body: fr
        ? "Parcourez les fonctions principales avec les données réelles de l’application. Le mode démo ne fabrique ni position, ni météo, ni résultat."
        : "Explore the main features using the app’s real data. Demo mode does not fabricate boat positions, weather, or results.",
    },
    {
      id: "live",
      action: "live",
      title: fr ? "Suivre l’expédition en direct" : "Follow the expedition live",
      body: fr
        ? "La carte suit la route Berry-Mappemonde. La position, l’horloge et les conditions proviennent des données chargées ; une donnée absente reste signalée comme absente."
        : "The map follows the Berry-Mappemonde route. Position, clock, and conditions come from loaded data; unavailable data stays explicitly unavailable.",
    },
    {
      id: "briefing",
      action: "briefing",
      title: fr ? "Briefing, récit et journal de bord" : "Briefing, story, and logbook",
      body: fr
        ? "Le panneau gauche rassemble le contexte « Ici », le briefing, le récit de l’expédition, les escales et le journal. Parcourez-le pour voir les éléments disponibles."
        : "The left panel brings together the “Here” context, briefing, expedition story, stopovers, and logbook. Browse it to inspect the information currently available.",
    },
    {
      id: "layers",
      action: "layers",
      title: fr ? "Carte et couches de données" : "Map and data layers",
      body: fr
        ? "Le panneau Outils expose les couches maritimes et scientifiques, les réglages et les sources. Activez une couche pour explorer la carte ; les crédits et avertissements restent ceux de l’application."
        : "The Tools panel exposes maritime and scientific layers, settings, and sources. Enable a layer to explore the map; attribution and safety warnings remain those of the app.",
    },
    {
      id: "replay",
      action: "replay",
      title: fr ? "Revoir l’expédition" : "Replay the expedition",
      body: replayReady
        ? (fr
            ? "Le film officiel est prêt. Lancez-le avec le bouton ci-dessous pour voir le bateau, les escales et le récit évoluer ensemble."
            : "The official film is ready. Start it below to see the boat, stopovers, and story evolve together.")
        : (fr
            ? "Le film utilise le stock officiel du serveur. Il n’est pas encore prêt dans cette session : le contrôle reste désactivé plutôt que de montrer une fausse démo."
            : "The film uses the server’s official store. It is not ready in this session yet, so the control stays disabled instead of showing a fake demo."),
    },
    {
      id: "trace",
      action: "trace",
      title: fr ? "Tracer sa propre route" : "Draw a custom route",
      body: fr
        ? "Le mode Tracer ouvre les outils de dessin. Cliquez sur la carte pour ajouter des points et observez le parcours se construire ; cette visite ne supprime aucun brouillon existant."
        : "Tracer opens the route-drawing tools. Click the map to add points and watch the route take shape; this walkthrough does not delete any existing draft.",
    },
    {
      id: "return",
      action: "return",
      title: fr ? "Retour à l’expédition" : "Return to the expedition",
      body: fr
        ? "Revenez à Suivre pour retrouver l’expédition Berry-Mappemonde. Terminer la visite ferme ce panneau sans effacer une route tracée."
        : "Return to Follow to see the Berry-Mappemonde expedition again. Finishing the tour closes this panel without clearing a drawn route.",
    },
  ];
}
