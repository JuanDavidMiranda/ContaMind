# Reglas de conciliación

La correspondencia no usa la posición de la fila. La clave es el número de documento normalizado: sin espacios, en mayúsculas y con los ceros iniciales intactos. No se convierte a número y no se eliminan prefijos como `FV` o `FE`. Un guion se conserva, así que `FV-001` y `FV001` siguen siendo documentos distintos.

## Normalización

- Identificaciones: se quitan espacios y puntos. El prefijo `NIT` se retira solo cuando el resto es numérico y puede incluir dígito de verificación. El valor sigue siendo texto.
- Fechas: se aceptan `AAAA-MM-DD` y fechas en las que el día o el mes sea mayor que 12. Si los dos primeros números pueden ser día o mes, la fecha queda ambigua y no se elige una interpretación.
- Importes: se usan `Decimal`. Si hay punto y coma, el separador de la derecha es el decimal. Un único separador con uno o dos dígitos finales es decimal. Varios separadores en grupos de tres son miles. Un separador seguido de exactamente tres dígitos queda ambiguo.
- Un importe recibido como `float` no se compara.

## Duplicados dentro de cada archivo

- Una sola fila con esa clave: caso único.
- Varias filas con los mismos valores normalizados: duplicado exacto. Se conserva un resultado y se listan todas las filas. No se borran.
- Varias filas con valores distintos, o con un valor que no se pudo interpretar: duplicado conflictivo. No se empareja automáticamente.

## Cruce entre fuentes

Solo se compara un campo si las dos fuentes tienen esa columna confirmada. Si falta en una, la regla se omite y queda registrada.

Cuando la clave existe en ambos lados y ninguno tiene un duplicado conflictivo:

1. Si algún valor necesario no se puede interpretar, la categoría principal es `REQUIRES_REVIEW`. Las diferencias de los campos válidos se conservan como señales.
2. Si la identificación difiere, la categoría principal es `THIRD_PARTY_MISMATCH`.
3. Si difiere la base, el IVA o el total por encima de la tolerancia, la categoría principal es `VALUE_MISMATCH`.
4. Si solo difiere la fecha, la categoría principal es `DATE_MISMATCH`.
5. Si todo lo comparable coincide, la categoría principal es `MATCHED`.

La tolerancia inicial es cero. Una diferencia igual a la tolerancia se considera coincidencia. La comparación usa `Decimal`, no punto flotante.

Si la clave solo está en el ERP, la categoría es `MISSING_IN_DIAN`. Si solo está en la DIAN, es `MISSING_IN_ERP`. Un duplicado conflictivo sin contraparte queda en `REQUIRES_REVIEW`, con el mensaje de que tampoco hubo correspondencia válida: no se presenta como una ausencia simple porque el grupo no es concluyente.

`POSSIBLE_DUPLICATE` acompaña a la categoría principal. No sustituye un cruce que sí fue concluyente.

## Conteos

- `erp_rows_read` y `dian_rows_read` cuentan las filas con algún dato.
- Las filas sin número de documento no entran al cruce y aparecen en los errores de validación.
- Cada número de documento produce un resultado, aunque tenga varias filas duplicadas.
- La categoría principal es excluyente.
- Las señales de valor, fecha, identificación y duplicado pueden coincidir en el mismo documento. Por eso su suma puede ser mayor que el número de resultados.
- Los indicadores salen de esos resultados. No se inventan valores para completar un campo vacío.
