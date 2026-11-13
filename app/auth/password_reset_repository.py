from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.auth.password_reset_models import PasswordResetTokenModel
from app.shared.datetimes import utc_now

class PasswordResetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, jti: UUID, user_id: UUID, expires_at: datetime) -> None:
        self.db.add(
        PasswordResetTokenModel(jti=jti, user_id=user_id, expires_at=expires_at)
        )
        self.db.flush()
    def consume(self, jti: UUID, user_id: UUID) -> bool:
        now = utc_now()
        stmt = (
            update(PasswordResetTokenModel)               # 1. "Voy a modificar la tabla de tokens..."
            .where(                                       # 2. "...pero SOLO la fila que cumpla TODO esto:"
                PasswordResetTokenModel.jti == jti,       #    - que sea este token
                PasswordResetTokenModel.user_id == user_id,  # - que sea de este usuario
                PasswordResetTokenModel.used_at.is_(None),   # - que NO se haya usado
                PasswordResetTokenModel.expires_at > now,    # - que NO haya vencido
            )
            .values(used_at=now)                          # 3. "...y le pongo la fecha de uso = ahora"
            .returning(PasswordResetTokenModel.jti)       # 4. "...y avísame qué fila cambiaste"
        )
        return self.db.execute(stmt).scalar() is not None
