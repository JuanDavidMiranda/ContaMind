# 0005. Ejecuciones de conciliación

Cada conciliación puede tener varias ejecuciones en `reconciliation_runs`. La ejecución guarda sus archivos, mapeos, reglas, resumen, resultados y errores. Una ejecución nueva no modifica las filas ni los archivos de una anterior, y no copia estados de revisión ni justificaciones.

La conciliación conserva el estado de la ejecución más reciente para la bandeja actual. El informe, si no recibe `run_id`, sale de la última ejecución terminada.

El avance de revisión manual se calcula al leer los resultados guardados. Solo entran los documentos cuya categoría principal no es `MATCHED`. `PENDING` e `IN_REVIEW` están pendientes. `JUSTIFIED` y `RESOLVED` cuentan como revisados. Si no hay documentos en ese grupo, la etiqueta es «No hay documentos pendientes de revisión». Esa cifra es distinta de la categoría del motor `REQUIRES_REVIEW`.

`total_delta` queda nulo cuando el documento no tiene correspondencia en una de las fuentes. No se guarda un cero en ese caso.

La migración `0002_reconciliation_runs` convierte cada conciliación ya existente en la ejecución número 1 y conserva los identificadores anteriores. `result_events` queda creada para el historial de revisión; todavía no tiene operaciones de alta.

La identidad sigue siendo el usuario local de desarrollo. No es autenticación de producción.
