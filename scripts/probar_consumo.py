import threading
import time
from datetime import timedelta
from uuid import uuid4

from app.auth.password import hash_password
from app.auth.password_reset_repository import PasswordResetRepository
from app.shared.database import SessionLocal
from app.shared.datetimes import utc_now
from app.users.users_models import UserModel

# 1. Preparar: crear un usuario y un jti de prueba en PostgreSQL.
with SessionLocal() as db:
    user = UserModel(
        name="Usuario Prueba",
        email=f"prueba-{uuid4()}@test.cl",
        passwordHash=hash_password("12345678"),
    )
    db.add(user)
    db.flush()
    jti = uuid4()
    PasswordResetRepository(db).add(jti, user.id, utc_now() + timedelta(minutes=15))
    db.commit()
    user_id = user.id

resultados = {}


# 2. Cada persona abre su propia transacción e intenta consumir el mismo jti.
def consumir(nombre, espera_antes_del_commit):
    with SessionLocal() as db:
        resultados[nombre] = PasswordResetRepository(db).consume(jti, user_id)
        time.sleep(espera_antes_del_commit)
        db.commit()


# A consume y espera 2 s antes del commit; B parte mientras tanto y queda esperando.
a = threading.Thread(target=consumir, args=("A", 2))
b = threading.Thread(target=consumir, args=("B", 0))
a.start()
time.sleep(0.5)
b.start()
a.join()
b.join()

print("Resultados:", resultados)

# 3. Limpiar: al borrar el usuario se borra su token (CASCADE).
with SessionLocal() as db:
    db.delete(db.get(UserModel, user_id))
    db.commit()

# 4. Comprobar.
assert resultados == {"A": True, "B": False}
print("✅ Solo una transacción logró consumir el token")
