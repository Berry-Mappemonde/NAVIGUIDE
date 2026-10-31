# Politique de sécurité / Security policy

## Périmètre / Scope

Cette politique couvre :

- le site [https://naviguide.fr](https://naviguide.fr) ;
- le code de ce dépôt (NAVIGUIDE).

This policy covers:

- the site [https://naviguide.fr](https://naviguide.fr);
- the code in this repository (NAVIGUIDE).

Hors périmètre : les autres sites et les services qui ne sont pas livrés par ce dépôt.

Out of scope: other sites and services that are not shipped from this repository.

## Versions supportées / Supported versions

| Version | Soutien / Supported |
| --- | --- |
| `main` | oui / yes |
| toute autre branche, étiquette ou archive / any other branch, tag, or archive | non / no |

## Signaler une vulnérabilité / Reporting a vulnerability

Écrivez à :

Write to:

clementfilisetti@berrymappemonde.org

N'ouvrez pas d'issue publique, et ne publiez ni détail ni correctif avant notre réponse.

Do not open a public issue, and do not publish details or a fix before we reply.

Le même contact est publié sur https://naviguide.fr/.well-known/security.txt (RFC 9116) une fois le vhost rechargé.

The same contact is published at https://naviguide.fr/.well-known/security.txt (RFC 9116) once the vhost is reloaded.

## Délai visé / Target response time

TODO (Berry) : indiquer le délai de première réponse et le délai de correction visés.

TODO (Berry): state the target time to a first response and the target time to a fix.

## Alertes connues / Known alerts

CodeQL analyse les pull requests. Les alertes détectées sont suivies dans l'onglet Security de GitHub et traitées dans les pull requests concernées.

CodeQL runs on pull requests. Findings are tracked in GitHub's Security tab and addressed in the relevant pull requests.

- `naviguide-simulator/server/story_cascade.py`
- `naviguide-simulator/server/escale_watch.py`
- `naviguide-simulator/server/tavily_client.py`

À la mise à jour Devpost, revérifier l'onglet Security. Si une alerte haute ou critique est ouverte sur l'un de ces fichiers, l'ajouter ici (fichier, règle, gravité). Ne jamais écrire la valeur d'un secret.

When Devpost is updated, recheck the Security tab. If a high or critical alert is open on one of these files, add it here (file, rule, severity). Never write the value of a secret.
