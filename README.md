# crewai-urban-explorer

Servicio Python (FastAPI + CrewAI) con 20 agentes especializados + 1 Director
de Contenido, organizados en **5 crews separados** que investigan, redactan
y publican contenido (POIs, eventos, negocios) para la app
[urban-explorer-ai](../urban-explorer-ai), vía el endpoint
`agent-content-ingest` de Supabase.

Este servicio es el lado que faltaba: `supabase/functions/crewai-trigger-refresh`
ya existe y corre todos los días a las 03:00 UTC vía pg_cron, pero hasta ahora
no tenía a quién llamar (`CREWAI_KICKOFF_WEBHOOK_URL` nunca estuvo configurado).
Desplegar este servicio y setear esa URL es lo que cierra el circuito.

## Arquitectura — 5 crews en vez de un crew único de 22 agentes

El diseño original (un solo crew secuencial de 22 agentes) hacía que abrir
una ciudad nueva tardara todo lo que tardara el pipeline completo. Ahora:

```
POST /ingest {city, country, lat, lng, mode?: "hiker"}
  → DiscoveryCrew (4 agentes, ~30s) — POIs/eventos/negocios básicos + clima
    ─┬─ EnrichmentCrew (5 agentes) → ContentCrew (5 agentes)
     │    lanzados juntos apenas termina Discovery. Content necesita el
     │    output de Enrichment (historia/horarios/precios), así que
     │    "en paralelo" acá significa "lanzados juntos", no "sin
     │    dependencia" — ver el comentario en main.py's
     │    _run_pipeline_for_city para el razonamiento completo.
     └─ HikerCrew (5 agentes) — solo si mode="hiker", arranca ya mismo,
          en paralelo real con todo lo demás (no depende de Discovery)
  → DirectorCrew (1 agente, siempre) — revisa todo lo anterior y es el
    único que llama a send_to_content_ingest
```

- **Discovery**: buscador_pois, buscador_eventos, buscador_negocios, clima_contexto
- **Enrichment**: enriquecedor_pois, investigador_historia, investigador_cultura, extractor_horarios, extractor_precios
- **Content**: redactor_contenido, personalizador_contenido, verificador_calidad, traductor_idiomas, generador_rutas_tematicas
- **Hiker**: buscador_senderos, verificador_rutas, clima_montana, identificador_plantas, guia_senderismo
- **Director**: director_contenido (meta-agente)

Cada crew es una instancia separada de `crewai.Crew` (ver `crew.py`) — el
encadenamiento nativo de CrewAI (`Task(context=[...])`) solo funciona
*dentro* de un mismo Crew, así que entre crews el output de uno se pasa
como texto plano inyectado en la descripción de las tareas del siguiente
(ver el docstring de `crew.py`).

**Límite conocido:** `HikerCrew` genera narrativa (historia, flora,
condiciones) pero no escribe en la tabla `hiking_routes` — esa tabla
necesita geometría real de sendero (`path`, `distance_km`,
`elevation_gain_m`) que ya calcula en tiempo real
`supabase/functions/hiking-routes`, y que este crew no tiene. El
`DirectorCrew` reporta el contenido de Hiker en su resumen pero no lo
inserta, para no degradar filas de las que depende la UI de la app.

**Modelos:** todos los agentes usan `claude-haiku-4-5-20251001` — es el
único modelo confirmado compatible con esta versión de CrewAI/litellm (ver
el docstring de `agents/_common.py` para el detalle completo de los
intentos con Sonnet 5 / Opus 5 que fallaron).

Ver [`.claude/skills/agentes-urban.md`](../urban-explorer-ai/.claude/skills/agentes-urban.md)
en el repo de la app para el contrato exacto de payloads de `agent-content-ingest`.

## Endpoints

- `GET /health` — liveness check.
- `POST /kickoff` — multi-ciudad, el que llama `crewai-trigger-refresh` vía
  pg_cron todos los días. Corre el mismo pipeline por-ciudad de abajo, una
  ciudad a la vez.
- `POST /ingest` — una sola ciudad, pensado para uso en tiempo real (ej. la
  app abriendo una ciudad nueva). Responde `202` de inmediato; Discovery
  suele terminar en menos de un minuto.
- `GET /status/{city}` — qué crews terminaron para esa ciudad (en memoria,
  se resetea si el proceso reinicia) + conteo real en Supabase de POIs/
  eventos/negocios para esa ciudad (esto sí sobrevive un reinicio).
- `GET /` — panel de admin.

## Desarrollo local

```bash
cp .env.example .env   # completar los 4 valores
pip install -r requirements.txt
uvicorn main:app --reload
```

Abrí `http://localhost:8000` para el panel de admin, o probá los endpoints:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Authorization: Bearer $CREWAI_KICKOFF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"city":"Granada","country":"Spain","lat":37.1773,"lng":-3.5986}'

curl http://localhost:8000/status/Granada
```

## Deploy en Railway

Con la [Railway CLI](https://docs.railway.app/guides/cli) instalada y logueada
(`railway login`), desde esta carpeta:

```bash
railway init && railway up
```

Eso crea el proyecto en Railway (usa `railway.toml`/`Dockerfile` de este repo)
y lo despliega. Después, seteá las 4 variables de entorno (una sola vez):

```bash
railway variables set SUPABASE_URL=https://wqsdtdvkqssjjucwjxgv.supabase.co
railway variables set SUPABASE_SERVICE_ROLE_KEY=<valor real>
railway variables set CREWAI_INGEST_SECRET=<mismo valor que el secret de Supabase>
railway variables set CREWAI_KICKOFF_TOKEN=<generá un valor random fuerte>
railway variables set ANTHROPIC_API_KEY=<mismo valor que el secret de Supabase>
railway up   # redeploy para que tome las variables
```

Los valores reales de `SUPABASE_SERVICE_ROLE_KEY`, `CREWAI_INGEST_SECRET` y
`ANTHROPIC_API_KEY` ya están seteados como secrets en el proyecto de Supabase
— consultalos con:

```bash
SUPABASE_ACCESS_TOKEN=<tu_token> npx supabase secrets list --project-ref wqsdtdvkqssjjucwjxgv
```

(no los pego en este README ni en ningún archivo del repo).

## Conectar el lado de Supabase (paso final, obligatorio)

Una vez desplegado, Railway te da una URL pública (`https://<algo>.up.railway.app`).
Con esa URL, en el repo `urban-explorer-ai`:

```bash
SUPABASE_ACCESS_TOKEN=<tu_token> npx supabase secrets set CREWAI_KICKOFF_WEBHOOK_URL=https://<tu-url>.up.railway.app/kickoff --project-ref wqsdtdvkqssjjucwjxgv
SUPABASE_ACCESS_TOKEN=<tu_token> npx supabase secrets set CREWAI_KICKOFF_TOKEN=<el mismo valor que usaste arriba en Railway> --project-ref wqsdtdvkqssjjucwjxgv
```

A partir de ahí, el cron diario de las 03:00 UTC ya llega hasta acá. Para
probarlo sin esperar al cron:

```bash
SUPABASE_ACCESS_TOKEN=<tu_token> npx supabase functions invoke crewai-trigger-refresh --project-ref wqsdtdvkqssjjucwjxgv
```

## Qué NO hace todavía este servicio

- No escribe en `approved_content` (tabla con `guide_character` pensada para
  narrativas por personaje) — ese endpoint/camino no existe todavía en
  `agent-content-ingest`, así que Content enriquece solo los campos reales
  del schema (`fun_fact`, `historical_period`, `accessibility_info`).
- No escribe en `hiking_routes` — ver "Límite conocido" arriba.
- `generador_rutas_tematicas` (rutas temáticas dentro de una ciudad, no
  senderismo) tampoco tiene tabla/endpoint de destino todavía en
  `agent-content-ingest` — el Director las reporta en su resumen pero no
  las persiste. Haría falta un nuevo `type` en ese endpoint para guardarlas.
- Este refactor a 5 crews no corrió nunca end-to-end contra el LLM real
  (mismo motivo de siempre: no hay intérprete de Python en el entorno
  donde se escribió). El diseño de un solo crew anterior sí llegó a correr
  exitosamente en producción antes de este refactor. Antes de confiar en
  el cron diario con esta versión, correlo una vez manualmente con
  `POST /ingest` para una sola ciudad y revisá `GET /status/{city}` y los
  logs de Railway.
