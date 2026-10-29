# 0003. Identidad de desarrollo

El MVP necesita relacionar usuarios, empresas y conciliaciones sin construir todavía un proveedor de autenticación. Se crean las tablas `users` y `company_memberships`. Al arrancar en desarrollo se siembra un usuario local estable.

Si la petición no trae `X-User-Id`, ese usuario representa al actor. Si la trae, debe existir y estar activo. En cualquier otro entorno, la ausencia de usuario responde 401. Las consultas filtran por membresía y responden 404 cuando el recurso pertenece a otra persona.

Esto permite probar el aislamiento entre empresas. No es un control de acceso de producción: la cabecera puede falsificarse y no hay sesión ni contraseña.
