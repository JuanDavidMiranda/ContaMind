# 0002. Clasificación de la conciliación

La clave de cruce es el número de documento normalizado, no la posición de la fila. Los campos adicionales validan la pareja; no sirven para unir documentos con números distintos.

Un documento puede tener varias diferencias. Se guarda una categoría principal, en el orden `REQUIRES_REVIEW`, `THIRD_PARTY_MISMATCH`, `VALUE_MISMATCH`, `DATE_MISMATCH` y `MATCHED`, y se conservan las demás como señales. `POSSIBLE_DUPLICATE` es una señal para no perder el hallazgo cuando el cruce principal ya es concluyente.

Los duplicados exactos se consolidan en un resultado y se listan todas las filas. Los duplicados con valores distintos no se emparejan. Los registros incompletos o ambiguos permanecen visibles en la validación.

La tolerancia monetaria inicial es cero y la aritmética es decimal. El texto que acompaña cada diferencia dice que se trata de una discrepancia para revisión.
