# Contribuer

## Branches

```
master (protégée) ← dev (protégée) ← release/vX.Y.Z ← issue-<numéro>
```

| Branche | Rôle | Créée depuis | Fusionnée dans |
|---|---|---|---|
| `master` | Code livré en production | — | — |
| `dev` | Intégration des releases validées | `master` | `master` |
| `release/vX.Y.Z` | Regroupe les tickets d'une même livraison | `dev` | `dev` |
| `issue-<numéro>` | Un ticket GitHub (ex. `issue-12`) | sa release | sa release |

**Ordre d'intégration :** `issue-<numéro>` → `release/vX.Y.Z` → `dev` → `master`

## Workflow

### 1. Démarrer un ticket

Chaque ticket correspond à une issue GitHub. La branche porte son numéro et part de la release concernée :

```bash
git fetch origin
git switch -c issue-12 origin/release/v0.1.0
```

### 2. Terminer un ticket

```bash
uv run ruff check --fix . && uv run ruff format . && uv run pytest
git push -u origin issue-12
```

Ouvrir une pull request **`issue-12` → `release/v0.1.0`**, avec `Closes #12` dans la description.

### 3. Livrer une release

- Quand tous les tickets de la release sont intégrés et validés : PR **`release/v0.1.0` → `dev`**.
- Après validation sur `dev` : PR **`dev` → `master`**.

> ⚠️ Un merge de `dev` vers `master` embarque **toutes** les releases déjà intégrées à `dev`. Ne merger dans `dev` que les releases prêtes à être livrées.

### Créer une release

```bash
git fetch origin
git switch -c release/v0.2.0 origin/dev
git push -u origin release/v0.2.0
```

## Règles de validation

- Toute intégration passe par une pull request, avec **une revue approuvée** et **la CI au vert** (lint, tests, build Docker).
- Aucun push direct sur `dev` ou `master` : GitHub le bloque.
- Les branches `dev` et `master` ne peuvent être ni supprimées ni réécrites (force push).

## Conflits

Les conflits se résolvent **sur la branche source**, en y intégrant la branche cible, puis on relance les tests :

```bash
# PR issue-12 → release/v0.1.0 en conflit
git switch issue-12
git fetch origin && git merge origin/release/v0.1.0
# résoudre, puis
uv run pytest && git push
```

Si la branche source est protégée (PR `dev` → `master`), on passe par une branche temporaire :

```bash
git switch -c fix-conflits-dev-master origin/dev
git merge origin/master
# résoudre, tester, pousser, puis ouvrir une PR fix-conflits-dev-master → dev
```

## Messages de commit

[Conventional Commits](https://www.conventionalcommits.org/fr/), avec le numéro du ticket :

```
feat(auth): ajout de l'inscription par email (#12)
fix(users): correction de la validation du pseudonyme (#15)
chore(ci): ajout du cache uv
```

## Migrations

- Toujours relire le fichier généré par `--autogenerate`.
- Si deux tickets d'une même release créent chacun une migration, le second à être mergé doit intégrer la release et corriger son `down_revision` (ou utiliser `alembic merge`).
