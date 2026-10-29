# Arquitectura del backend

`backend/app/main.py` solo crea la aplicación, el CORS, el ciclo de vida y los manejadores de error. Las rutas viven en los módulos.

| Carpeta | Responsabilidad |
|---|---|
| `app/api` | Dependencias HTTP, incluido el usuario actual |
| `app/core` | Configuración, errores y logging |
| `app/db` | Sesión SQLAlchemy y registro de modelos |
| `app/modules/identity` | Usuario local de desarrollo |
| `app/modules/companies` | Empresas y membresías |
| `app/modules/reconciliations/engine` | Reglas puras de normalización y conciliación |
| `app/modules/reconciliations/application` | Casos de uso |
| `app/modules/reconciliations/infrastructure` | Lectura de archivos, disco, ORM e informe Excel |
| `app/modules/reconciliations/api` | Rutas REST |
| `app/modules/ai` | Puerto para un analizador futuro |

El motor solo depende de la biblioteca estándar. La lectura de CSV usa Pandas y la de Excel usa openpyxl, ambas fuera del motor. Las fórmulas y las macros se rechazan; no se ejecutan.

La persistencia usa SQLAlchemy 2 y Alembic. Los identificadores son UUID. Los montos de la comparación usan `Decimal`. Los resultados guardan la categoría principal, las señales, los valores originales, los valores normalizados y las filas de origen.

Los errores de aplicación responden con `{"error": {"code", "message", "details"}}`. Un fallo de base de datos responde 500 con un mensaje estable y el detalle técnico se queda en el log.
