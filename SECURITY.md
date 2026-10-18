# Politique de sécurité / Security policy

## Périmètre / Scope

Cette politique couvre :

- le site [https://naviguide.fr](https://naviguide.fr) ;
- le dépôt [Berry-Mappemonde/NAVIGUIDE](https://github.com/Berry-Mappemonde/NAVIGUIDE).

This policy covers:

- the site [https://naviguide.fr](https://naviguide.fr);
- the repository [Berry-Mappemonde/NAVIGUIDE](https://github.com/Berry-Mappemonde/NAVIGUIDE).

Hors périmètre : les autres sites et les services qui ne sont pas livrés par ce dépôt.

Out of scope: other sites and services that are not shipped from this repository.

## Versions supportées / Supported versions

| Version | Soutien / Supported |
| --- | --- |
| `main` | oui / yes |
| toute autre branche, étiquette ou archive / any other branch, tag, or archive | non / no |

## Signaler une vulnérabilité / Reporting a vulnerability

Utilisez le formulaire privé GitHub :

Use the private GitHub form:

https://github.com/Berry-Mappemonde/NAVIGUIDE/security/advisories/new

N'ouvrez pas d'issue publique, et n'envoyez pas de correctif public avant qu'un avis privé existe.

Do not open a public issue, and do not send a public fix before a private advisory exists.

Le même contact est publié sur https://naviguide.fr/.well-known/security.txt (RFC 9116) une fois le vhost rechargé.

The same contact is published at https://naviguide.fr/.well-known/security.txt (RFC 9116) once the vhost is reloaded.

## Délai visé / Target response time

TODO (Berry) : indiquer le délai de première réponse et le délai de correction visés.

TODO (Berry): state the target time to a first response and the target time to a fix.

## Alertes connues / Known alerts

Au 18 octobre 2026, ce dépôt n'a pas encore de résultat CodeQL publié. Aucune alerte de gravité haute ou critique n'est donc consignée sur :

As of 18 October 2026, this repository has no published CodeQL result yet. No high or critical alert is recorded on:

- `naviguide-simulator/server/story_cascade.py`
- `naviguide-simulator/server/escale_watch.py`
- `naviguide-simulator/server/tavily_client.py`

À la mise à jour Devpost, revérifier l'onglet Security. Si une alerte haute ou critique est ouverte sur l'un de ces fichiers, l'ajouter ici (fichier, règle, gravité). Ne jamais écrire la valeur d'un secret.

When Devpost is updated, recheck the Security tab. If a high or critical alert is open on one of these files, add it here (file, rule, severity). Never write the value of a secret.
