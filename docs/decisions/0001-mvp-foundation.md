# 0001. Fundación del monorepo

El repositorio estaba vacío, solo con `git init` en `master`. El código vive en la raíz de ese repositorio, no dentro de una carpeta adicional `contamind-ai/`, porque el proyecto ya es el repositorio abierto en Cursor.

Se usa un monolito modular: Next.js y FastAPI en el mismo repositorio, PostgreSQL 16 en Docker y archivos privados en `storage/`. No hay microservicios ni colas. La conciliación del MVP es síncrona y rechaza archivos de más de 10 MB o 10 000 filas.

Python se declara compatible con 3.12 o superior. El entorno local de desarrollo usa el intérprete 3.14 disponible en la máquina. La imagen Docker del backend fija Python 3.12.
