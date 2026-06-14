# drivers/

El proyecto usa **nzpy** (conector Python puro) — normalmente **no necesitas nada aquí**.

Solo si usas el fallback **JDBC**, coloca el driver propietario de IBM en esta carpeta:

    backend/drivers/nzjdbc.jar

⚠️ El `.jar` está en `.gitignore` (es propietario de IBM, **no se redistribuye** en el repo).
Cada quien lo obtiene de su instalación de Netezza / IBM.
