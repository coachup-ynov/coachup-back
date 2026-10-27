# Importer ici chaque modèle pour qu'Alembic le détecte en autogenerate
from app.db.base import Base
from app.models.session import UserSession
from app.models.user import Level, User, Visibility

__all__ = ["Base", "Level", "User", "UserSession", "Visibility"]
