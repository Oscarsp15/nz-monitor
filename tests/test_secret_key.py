"""La app se niega a arrancar con la SECRET_KEY por defecto.

Ese valor vive en el código fuente (público), así que con él cualquiera puede firmar un JWT de
administrador y entrar sin credenciales. Se detectó probando la API real, no en revisión.
"""
import pytest

from config import DEFAULT_SECRET_KEY, InsecureSecretKeyError, Settings, check_secret_key


def test_la_clave_por_defecto_aborta_el_arranque():
    with pytest.raises(InsecureSecretKeyError):
        check_secret_key(Settings(secret_key=DEFAULT_SECRET_KEY))


def test_la_clave_vacia_tambien_aborta():
    with pytest.raises(InsecureSecretKeyError):
        check_secret_key(Settings(secret_key="   "))


def test_una_clave_propia_pasa():
    check_secret_key(Settings(secret_key="una-clave-larga-y-propia-de-verdad"))


def test_el_env_se_resuelve_por_ruta_absoluta():
    """Arrancar desde `backend/` o desde la raíz debe leer los mismos archivos."""
    files = Settings.model_config["env_file"]
    assert all(str(f) == str(f) and f.is_absolute() for f in files)
