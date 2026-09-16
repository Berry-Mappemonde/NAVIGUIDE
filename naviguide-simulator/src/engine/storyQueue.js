/**
 * E5 socket. Today a no-op.
 * Later: usual cascade NIM → OpenRouter (± :online) → Claude
 * on the event JSON already collected.
 * Not Nemotron. Not Token Factory. Not Tavily world-search.
 * Play never awaits this.
 */

export function enqueueStory(_eventJson) {
  return {
    status: "template",
    tavily: null,
    nvidia: null,
    cascade: "nim-or-claude",
  };
}
