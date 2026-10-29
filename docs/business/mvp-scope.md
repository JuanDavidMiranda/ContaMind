# Alcance del MVP 1

Incluido:

- Empresas con razón social, identificación tributaria opcional, estado y fecha de creación.
- Relación usuario-empresa, con un usuario local de desarrollo.
- Conciliación de ventas por periodo, con un archivo ERP y un archivo DIAN en CSV o XLSX.
- Sugerencia y confirmación de columnas.
- Normalización, duplicados, cruce por número de documento e informe Excel.
- Historial de conciliaciones y detalle de cada resultado.

Fuera de este MVP:

- Autenticación real, contraseñas, OAuth y roles distintos de `owner`.
- Ejecución en cola para archivos que superen 10 MB o 10 000 filas.
- Conectores directos al ERP o a la DIAN.
- Corrección automática de comprobantes.
- Un agente que clasifique diferencias o dictamine obligaciones tributarias.

El estado `running` ya existe para poder mover la ejecución a un proceso aparte sin cambiar el modelo.
