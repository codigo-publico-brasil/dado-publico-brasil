"""Sensor que avisa das verificações de ativo em erro (a execução segue SUCCESS: nada é bloqueado)."""

import os
from datetime import datetime, timedelta

from dagster import (
    AssetCheckEvaluation,
    AssetCheckSeverity,
    DagsterEventType,
    DefaultSensorStatus,
    EventRecordsFilter,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

from dado_publico_brasil.core import alert


def _text(evaluation: AssetCheckEvaluation) -> str:
    detail = evaluation.metadata.get("detalhes")
    return str(evaluation.description or (detail.value if detail else ""))


@sensor(name="verificacoes_em_erro", default_status=DefaultSensorStatus.RUNNING, minimum_interval_seconds=300)
def failed_checks(context: SensorEvaluationContext) -> SkipReason:
    """Avisa das verificações de ativo reprovadas com severidade ERROR (a execução segue SUCCESS).

    Um aviso por tique, com todos os ativos; o cursor é o instante do último evento lido (nada se repete).
    Sem cursor (primeira vez), olha as últimas 24 h. Sem SMTP o aviso fica no log do tique e na mensagem dele.
    """
    # Cursor por instante: o de id exige cursor próprio quando o armazenamento é por execução.
    after = float(context.cursor) if context.cursor else (datetime.now() - timedelta(hours=24)).timestamp()
    filtro = EventRecordsFilter(DagsterEventType.ASSET_CHECK_EVALUATION, after_timestamp=after)
    records = context.instance.event_log_storage.get_event_records(filtro, limit=1000, ascending=True)
    if not records:
        return SkipReason("sem avaliações novas")
    context.update_cursor(str(max(r.timestamp for r in records)))
    items = sorted(
        {
            (e.asset_key.to_user_string(), e.check_name, _text(e))
            for r in records
            if (e := r.event_log_entry.asset_check_evaluation)
            and not e.passed
            and e.severity == AssetCheckSeverity.ERROR
        }
    )
    if not items:
        return SkipReason(f"{len(records)} avaliações novas, nenhuma em erro")
    base = os.environ.get("DADO_PUBLICO_DAGSTER_URL")
    sent = alert.notify_check_errors(items, f"{base.rstrip('/')}/assets" if base else None)
    summary = chr(10).join(f"{a} / {c}: {t[:200]}" for a, c, t in items)
    context.log.error(
        f"{len(items)} verificação(ões) em erro (e-mail {'enviado' if sent else 'não enviado'}):"
        + chr(10)
        + summary
    )
    return SkipReason(f"{len(items)} verificação(ões) em erro: " + "; ".join(a for a, _, _ in items)[:500])
