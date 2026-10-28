import { Component } from "react";

/**
 * Filet d'un panneau (#101) : une erreur de rendu dans le volet gauche, les outils ou la barre du film
 * ne démonte plus tout l'arbre — la carte et le reste du cockpit continuent. Rien d'ajouté à l'écran
 * tant que tout va bien ; en cas d'erreur, une ligne et un bouton qui remonte le panneau.
 * Composant classe : React n'offre pas de frontière d'erreur en hook.
 */
export class PanelBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
    this.reset = this.reset.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error(`[naviguide] panneau « ${this.props.name || "?"} » en erreur`, error, info?.componentStack);
  }

  reset() {
    this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div
        role="alert"
        data-testid="panel-boundary"
        data-panel={this.props.name || ""}
        className="absolute z-[2100] left-3 top-3 max-w-xs rounded-md border border-amber-400/40 bg-slate-900/90 px-3 py-2 text-xs text-amber-100 shadow"
      >
        <span>{this.props.message || "This panel hit an error."}</span>{" "}
        <button type="button" className="underline font-semibold" onClick={this.reset}>
          {this.props.retryLabel || "Reload panel"}
        </button>
      </div>
    );
  }
}

/**
 * Dernier filet, autour de toute l'application : hors du LangProvider, d'où le texte en deux langues.
 */
export class RootBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("[naviguide] erreur de rendu de l'application", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div
        role="alert"
        data-testid="root-boundary"
        style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#0b1f3a", color: "#e2e8f0", fontFamily: "system-ui, sans-serif", padding: 16, textAlign: "center" }}
      >
        <div>
          <p style={{ margin: 0 }}>NAVIGUIDE hit an error. · NAVIGUIDE a rencontré une erreur.</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{ marginTop: 12, padding: "8px 16px", borderRadius: 6, border: "1px solid #94a3b8", background: "transparent", color: "inherit", cursor: "pointer" }}
          >
            Reload · Recharger
          </button>
        </div>
      </div>
    );
  }
}
