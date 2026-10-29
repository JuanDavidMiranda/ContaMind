# Integración futura de inteligencia artificial

La comparación de documentos es determinista. No usa un modelo para decidir si dos importes coinciden, si una fecha es válida o si un documento falta.

El puerto `DifferenceAnalyzer` en `backend/app/modules/ai/application/ports.py` recibe una categoría, señales y diferencias ya calculadas, y puede devolver una nota explicativa. `UnavailableDifferenceAnalyzer` existe para dejar el contrato probado sin proveedor.

Cuando haya una tarea justificada:

1. Añadir LangGraph u Ollama como dependencia opcional, no como requisito del arranque.
2. Implementar el puerto en un proveedor nuevo, por ejemplo `app/modules/ai/providers/ollama.py`.
3. Exponer un endpoint aparte que llame al analizador sobre resultados ya guardados.
4. Mostrar la nota como explicación, sin cambiar `primary_category`, los importes ni el informe determinista.

El motor no debe importar ese proveedor. La prueba `test_boundaries.py` vigila que el paquete `engine` no referencie FastAPI, SQLAlchemy, LangGraph ni Ollama.
