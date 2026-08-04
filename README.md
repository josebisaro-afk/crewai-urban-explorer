# crewai-urban-explorer

Servicio Python (FastAPI + CrewAI) con los 22 agentes ("URBAN EXPLORER AI -
Production Ready Meta-Agente Universal": 21 especialistas + 1 Director de
Contenido) que investigan, redactan y publican contenido (POIs, eventos,
negocios) para la app [urban-explorer-ai](../urban-explorer-ai), vía el
endpoint `agent-content-ingest` de Supabase.

Este servicio es el lado que faltaba: `supabase/functions/crewai-trigger-refresh`
ya existe y corre todos los días a las 03:00 UTC vía pg_cron, pero hasta ahora
no tenía a quién llamar (`CREWAI_KICKOFF_WEBHOOK_URL` nunca estuvo configurado).
Desplegar este servicio y setear esa URL es lo que cierra el circuito.

## Arquitectura

```
pg_cron (03:00 UTC diario)
  → crewai-trigger-refresh (edge function, lee city_index)
    → POST /kickoff  [ESTE SERVICIO]
      → crew.py: por cada ciudad, un Crew secuencial de 22 agentes
        1. 16 agentes de investigación (Wikipedia + Overpass)
        2. Redactor → Personalizador → Agente de Idioma
        3. Verificación de Datos → Calidad y Ranking
        4. Director de Contenido → send_to_content_ingest
          → agent-content-ingest (edge function) → Postgres
```

Ver [`.claude/skills/agentes-urban.md`](../urban-explorer-ai/.claude/skills/agentes-urban.md)
en el repo de la app para el contrato exacto de payloads.

## Desarrollo local

```bash
cp .env.example .env   # completar los 4 valores
pip install -r requirements.txt
uvicorn main:app --reload
```

Abrí `http://localhost:8000` para el panel de admin, o probá el endpoint:

```bash
curl -X POST http://localhost:8000/kickoff \
  -H "Authorization: Bearer $CREWAI_KICKOFF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"trigger":"manual_test","cities":[{"city":"Granada","country":"Spain","lat":37.1773,"lng":-3.5986}]}'
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
  `agent-content-ingest`, así que el Personalizador enriquece solo los campos
  reales del schema (`fun_fact`, `historical_period`, `accessibility_info`).
- No corrió nunca contra el LLM real — está escrito siguiendo la API
  documentada de CrewAI/FastAPI/supabase-py, pero no fue ejecutado end-to-end
  (requiere las 4 variables de entorno reales, que no están disponibles en el
  entorno donde se escribió este servicio). Antes de confiar en el cron
  diario, correlo una vez manualmente para una sola ciudad y revisá el panel
  de admin y los logs de Railway.
