# Contribuer

## Branches

- `main` : code en production, protégé. On n'y pousse jamais directement.
- `develop` : branche d'intégration. Toutes les PR partent de et visent `develop`.
- `feature/<sujet>` : nouvelle fonctionnalité (ex. `feature/inscription`).
- `fix/<sujet>` : correction de bug.
- `chore/<sujet>` : infra, CI, dépendances, docs.

`develop` est fusionnée dans `main` lors d'une mise en production.

## Workflow

```bash
git switch develop && git pull
git switch -c feature/inscription
# ... développement ...
uv run ruff check --fix . && uv run ruff format . && uv run pytest
git push -u origin feature/inscription
# ouvrir une PR vers develop
```

Une PR doit :
- passer la CI (lint + tests + build Docker) ;
- être relue et approuvée par au moins une personne ;
- inclure la migration Alembic si le modèle de données change.

## Messages de commit

[Conventional Commits](https://www.conventionalcommits.org/fr/) :

```
feat(auth): ajout de l'inscription par email
fix(users): correction de la validation du pseudonyme
chore(ci): ajout du cache uv
docs: mise à jour du README
test(auth): tests de connexion
```

## Migrations

- Une migration par PR maximum quand c'est possible.
- Toujours relire le fichier généré par `--autogenerate`.
- Si deux PR créent chacune une migration, la seconde à être fusionnée doit rebaser et corriger son `down_revision` (ou utiliser `alembic merge`).
