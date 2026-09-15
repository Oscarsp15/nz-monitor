# Agentes del proyecto

Roles versionados para que el criterio de cada capa viva en el repo y no se reinvente en cada
sesión: `backend-netezza`, `frontend-ux`, `diseno-responsive`, `qa-seguridad`, `revisor`.

## Regla de uso: se reanuda, no se rearranca

Un agente que ya trabajó **conserva su transcript**. Reanudarlo cuesta una fracción de lo que cuesta
uno nuevo, que tendría que volver a leer `AGENTS.md`, redescubrir la estructura y repetir las
mediciones que el otro ya hizo.

- **Segunda tanda sobre lo mismo → reanudar** al agente que lo construyó. Sabe qué tocó, qué decidió
  y por qué; y detecta sus propias regresiones.
- **Volver a verificar tras un cambio → reanudar al de QA.** Ya tiene la matriz de permisos, los
  usuarios de prueba que creó y los intentos de bypass que probó.
- **Agente nuevo solo** cuando el trabajo es de otra capa o el contexto anterior estorba más de lo
  que ayuda.

## Reparto de coste

Modelo caro donde un error sale caro (SQL contra el appliance, revisión final antes del merge);
modelo barato donde el trabajo es mecánico y lo verifica una herramienta (`tsc`, `lint`, `build`).

## Lo que ningún agente hace

Commit, push, ni abrir PR. Entregan el árbol de trabajo y un informe; el commit lo decide quien
orquesta, que es quien ve el conjunto.
