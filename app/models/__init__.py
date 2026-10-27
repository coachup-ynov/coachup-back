# Importer ici chaque modèle pour qu'Alembic le détecte en autogenerate
from app.db.base import Base
from app.models.user import User

__all__ = ["Base", "User"]
