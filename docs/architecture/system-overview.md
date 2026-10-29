# Visión del sistema

ContaMind AI es un monolito modular. El navegador habla con Next.js y Next.js reenvía `/api` a FastAPI. FastAPI orquesta empresas, archivos y conciliaciones. El motor de conciliación compara registros ya normalizados y no conoce HTTP, base de datos ni modelos de lenguaje.

```text
Navegador
  -> Next.js (interfaz y proxy /api)
    -> FastAPI (casos de uso, autorización por empresa, almacenamiento)
      -> Motor de conciliación (normalización, cruce, clasificación)
      -> PostgreSQL (empresas, conciliaciones, resultados, eventos)
      -> storage/ (archivos privados, nombre interno UUID)
```

La inteligencia artificial queda detrás de un puerto que la conciliación no invoca. Así se puede añadir un explicador más adelante sin cambiar las reglas matemáticas.

## Límites de seguridad de este MVP

- El entorno de desarrollo acepta al usuario local sembrado al arrancar y, si se envía, la cabecera `X-User-Id`.
- Cada consulta de empresas, archivos, resultados e informes comprueba la membresía usuario-empresa.
- Un identificador de otra empresa responde 404.
- Los archivos no se descargan por ruta. El informe se genera a partir del identificador de la conciliación.
- Fuera de `development`, una petición sin usuario recibe 401.

Estas medidas preparan la autorización. No reemplazan autenticación, sesiones ni cifrado de secretos de producción.
