# ContaMind AI

MVP de conciliación de ventas entre un archivo exportado de un ERP y un archivo de facturación electrónica de la DIAN.

El sistema normaliza ambos archivos, propone la correspondencia de columnas, compara los documentos con reglas deterministas y entrega un informe para revisión. Una diferencia es una discrepancia; no es un incumplimiento tributario ni un error contable confirmado.

Esta versión no está apta para producción. La autenticación es un usuario local de desarrollo y el acceso se aísla por empresa para poder sustituirlo después por sesiones reales.

## Requisitos

- Docker Desktop, para PostgreSQL 16
- Python 3.12 o superior. En esta máquina el lanzador `py -3.14` funciona con las dependencias actuales
- Node.js 20 o superior y npm

## Configuración

Desde la raíz del repositorio:

```powershell
Copy-Item .env.example .env
docker compose up -d db
```

Backend:

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

Frontend, en otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abre `http://localhost:3000`. La interfaz llama a `/api/v1` y Next.js reenvía esas rutas a `http://127.0.0.1:8000`.

También puedes construir el backend con Docker. El servicio `backend` de `docker-compose.yml` aplica las migraciones al arrancar. El frontend sigue ejecutándose en el host durante el desarrollo.

## Pruebas

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

```powershell
cd frontend
npm test
```

Las pruebas usan datos sintéticos. No cargues información contable real en el repositorio.

## Flujo del MVP

1. Crear una empresa.
2. Crear una conciliación con el periodo y los dos archivos, CSV o XLSX.
3. Revisar y confirmar las columnas sugeridas.
4. Ejecutar la conciliación.
5. Filtrar resultados, abrir el detalle y descargar el Excel.

Los archivos quedan en el directorio privado `storage/`, fuera de la carpeta pública del frontend. Ese directorio no se versiona.

## Límites actuales

- No hay inicio de sesión, contraseñas ni roles finos. En `APP_ENV=development` se usa el usuario local documentado en `.env.example`.
- La conciliación corre dentro de la petición HTTP, con un máximo de 10 MB y 10 000 filas por archivo.
- No hay conexión directa con un ERP ni con la DIAN.
- LangGraph y Ollama no participan en la comparación. El contrato futuro está en `backend/app/modules/ai/application/ports.py`.

La documentación de arquitectura, reglas y API está en `docs/`.
