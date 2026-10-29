# Convenciones de la API

Prefijo: `/api/v1`.

Los cuerpos de error tienen esta forma:

```json
{"error": {"code": "not_found", "message": "La conciliación no existe o no tienes acceso.", "details": null}}
```

| Código | Uso |
|---|---|
| 200 | Consulta o actualización correcta |
| 201 | Empresa o conciliación creada |
| 401 | Falta un usuario válido |
| 404 | El recurso no existe para el usuario actual |
| 409 | El estado no permite la operación |
| 422 | Archivo, columnas o datos de entrada inválidos |
| 500 | Error interno o de base de datos, sin detalle SQL |

## Rutas

| Método | Ruta | Función |
|---|---|---|
| GET | `/health` | Estado de la aplicación. Pública. `production_ready` es falso |
| GET | `/me` | Usuario actual y el modo de autenticación |
| GET, POST | `/companies` | Listar y crear empresas del usuario |
| GET, PATCH | `/companies/{id}` | Consultar o actualizar una empresa propia |
| GET, POST | `/reconciliations` | Historial y creación. La creación recibe empresa, periodo y tolerancia |
| GET | `/reconciliations/{id}` | Estado, archivos, resumen y reglas |
| POST | `/reconciliations/{id}/files` | Carga multipart con `source=erp` o `source=dian` |
| GET | `/reconciliations/{id}/columns` | Encabezados, muestra y sugerencias |
| PUT | `/reconciliations/{id}/mapping` | Confirmación de columnas de ambas fuentes |
| POST | `/reconciliations/{id}/run` | Ejecuta la conciliación |
| GET | `/reconciliations/{id}/results` | Página de resultados de la ejecución más reciente. Acepta `page`, `page_size`, `category` y `q` |
| GET | `/reconciliations/{id}/results/{result_id}` | Detalle de un resultado de cualquier ejecución de esa conciliación |
| GET | `/reconciliations/{id}/report` | Excel de una ejecución terminada. Sin `run_id`, usa la última terminada |

`category=MATCHED`, `MISSING_IN_DIAN` y `MISSING_IN_ERP` filtran la categoría principal. `VALUE_MISMATCH`, `DATE_MISMATCH`, `THIRD_PARTY_MISMATCH`, `POSSIBLE_DUPLICATE` y `REQUIRES_REVIEW` también incluyen documentos que llevan esa señal aunque su categoría principal sea otra.

La búsqueda `q` normaliza espacios y mayúsculas igual que el número de documento. No recupera un documento distinto por quitar ceros iniciales.

El informe neutraliza celdas de texto que empiezan por `=`, `+`, `-` o `@` para que Excel no las ejecute como fórmulas.
