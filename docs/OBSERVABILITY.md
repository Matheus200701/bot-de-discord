# Observabilidade — Fase 11

## Stack

- OpenTelemetry SDK para traces e métricas.
- Instrumentação FastAPI, SQLAlchemy e HTTPX.
- Sentry opcional para exceções e tracing de aplicação.
- `sitecustomize.py` inicializa a telemetria antes dos imports da aplicação.

OpenTelemetry é inicializado somente com exporters configurados. Isso mantém desenvolvimento local silencioso e permite enviar OTLP para um Collector ou backend gerenciado.

## Variáveis

```dotenv
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.05
SENTRY_PROFILES_SAMPLE_RATE=0
OTEL_SERVICE_NAME=discord-commerce-platform
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=
OTEL_EXPORTER_OTLP_HEADERS=
```

Nunca coloque tokens Discord, segredos PSP, cookies ou payloads financeiros em atributos de span. A integração Sentry desabilita PII padrão e remove cookies, headers e request data antes do envio.

## Dimensões recomendadas

Use cardinalidade controlada:

- `deployment.environment.name`
- `service.name`
- `service.version`
- `http.request.method`
- `http.response.status_code`
- `url.template`
- `commerce.operation`
- `commerce.provider`

Evite `discord_user_id`, e-mail, token, código PIX e identificadores de sessão como labels/métricas de alta cardinalidade.

## SLOs iniciais

| Indicador | SLO | Alerta |
|---|---:|---:|
| Disponibilidade API | >= 99,9% | < 99,5% em 15 min |
| Erros HTTP 5xx | < 0,5% | >= 2% em 10 min |
| Latência p95 API | < 750 ms | >= 1,5 s em 10 min |
| Falhas de webhook PSP | < 0,5% | >= 2% em 10 min |
| Outbox DEAD | 0 | >= 1 imediatamente |
| Pagamentos pendentes | tendência estável | crescimento contínuo por 15 min |
| Falhas de fulfillment | < 1% | >= 3% em 15 min |

## Alertas prioritários

1. **Outbox DEAD > 0:** pagamentos, refunds ou entregas podem estar parados; investigar `last_error`, provider status e tentar replay controlado.
2. **Webhook 5xx elevado:** verificar assinatura, conectividade com PostgreSQL e PSP.
3. **Latência p95 elevada:** separar tempo de banco, PSP e Discord via spans.
4. **Pagamento pendente crescendo:** verificar indisponibilidade do PSP e o reconciliador.
5. **Fulfillment falhando:** verificar permissões do bot, hierarquia de cargos e configuração do produto.
6. **Erros de autenticação OAuth elevados:** verificar redirect URI, client secret e disponibilidade da API Discord.

## Privacidade

A telemetria não deve ser usada como armazenamento de auditoria financeira. Ledger, pedidos, refunds e audit logs continuam no PostgreSQL. Observabilidade deve conter somente o contexto técnico necessário para diagnóstico.

## Runbook

Ao receber um alerta, correlacione `trace_id` com logs estruturados, identifique o serviço (`api`, `worker`, `bot`), confirme dependências (`postgres`, `redis`, PSP/Discord) e só então execute reprocessamentos. Nunca faça replay manual de eventos financeiros sem conferir a idempotência do agregado.
