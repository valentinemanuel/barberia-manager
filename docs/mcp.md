# Herramientas MCP del proyecto

La plantilla `opencode.json.example` recupera la configuración documental de la rama histórica `feat/mcp-config-y-offline`, adaptada al formato nativo de OpenCode V2. No contiene credenciales y no se carga automáticamente como configuración.

## Preparación

1. Instalar Node.js/npm para los servidores que utilizan `npx`; instalar `uv` (incluye `uvx`) si se utilizará SQLite.
2. Trabajar desde la raíz del proyecto. Si no existe `opencode.json`, copiar la plantilla a ese nombre. Si ya existe, integrar únicamente los servidores necesarios sin sobrescribir agentes, permisos ni otras opciones locales.
3. En OpenCode V2, los servidores se definen bajo `mcp.servers`. `disabled: true` evita su conexión; omitirlo o usar `false` permite conectarlos.
4. SQLite y GitHub están desactivados en la plantilla. Activarlos solo después de completar los requisitos correspondientes.

## Servidores

| Servidor | Uso | Requisitos y precauciones |
|---|---|---|
| context7 | Documentación de librerías | Node.js/npm y acceso a internet para descargar/iniciar el paquete. |
| playwright | Navegador y pruebas E2E | Node.js/npm y navegador compatible; comprobar la conexión antes de ejecutar pruebas. Usar en lugar de `chrome-devtools-mcp`, descartado por inestabilidad con Edge. |
| sqlite | Inspección de la base local | `uvx` y la base `backend/barberia.db`. La ruta es relativa a la raíz del workspace. No activar en un worktree sin la base: no copiar datos reales ni crear/modificar una base sin autorización. |
| github | Consulta y gestión del repositorio | Definir `GITHUB_PERSONAL_ACCESS_TOKEN` en el entorno antes de iniciar OpenCode, con los permisos mínimos necesarios. La plantilla utiliza sustitución `{env:GITHUB_PERSONAL_ACCESS_TOKEN}`, no un token literal. |

El servidor SQLite quedó verificado el 2026-10-09 con `mcp-server-sqlite` 2025.4.25 y los pines `mcp==1.9.4` y `pydantic==2.11.7`. Los pines son obligatorios: `pydantic` ≥2.12 eliminó `eval_type_backport` (error de importación con `mcp` ≤1.15) y `mcp` ≥1.16 eliminó `Server.list_resources` (que `mcp-server-sqlite` 2025.4.25 sigue usando). Sin los pines, `uvx` resuelve `pydantic` 2.14 y el servidor falla al iniciar. En este entorno `uvx` no está en el PATH; la configuración local usa la ruta absoluta del directorio `Scripts` del Python de Microsoft Store.

## Verificación

- Ejecutar `opencode mcp list` desde el proyecto y revisar el estado de cada servidor.
- Usar `/mcps` para gestionar conexiones. Un servidor configurado no equivale a uno conectado o probado.
- Comprobar que `opencode.json` siga ignorado por Git antes de cualquier commit. Nunca versionar tokens, credenciales OAuth ni datos personales.
- Mantener `AGENTS.md`, `MEMORY.md` y esta plantilla coherentes cuando cambien las herramientas. No marcar tests o conexiones como completados sin evidencia.

## Referencias

- [Configuración de OpenCode V2](https://opencode.ai/v2/docs/config)
- [Servidores MCP en OpenCode V2](https://opencode.ai/v2/docs/mcp-servers)

Este cambio solo incorpora documentación y una plantilla; no migra ni altera la configuración local existente.
