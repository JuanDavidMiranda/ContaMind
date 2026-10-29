# 0004. Frontera con la inteligencia artificial

LangGraph y Ollama no se instalan en este MVP. La comparación de importes, fechas e identificaciones debe poder probarse sin un modelo.

El módulo `app/modules/ai` define el puerto `DifferenceAnalyzer` y una implementación que no produce notas. La ejecución de la conciliación no lo llama. Un proveedor futuro puede explicar diferencias ya clasificadas, sin autoridad para cambiar la categoría ni los valores.
