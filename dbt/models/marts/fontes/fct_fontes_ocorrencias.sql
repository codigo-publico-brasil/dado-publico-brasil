-- Ocorrências das fontes: cada sequência de verificações seguidas que não deu "ok" para a mesma fonte, dataset,
-- partição e verificação é UMA ocorrência (primeira e última observação, como o first_seen/last_seen do OpenSanctions).
-- Um "ok" depois encerra a ocorrência; um problema novo depois do "ok" abre outra. O tipo vem do nome e do resultado
-- da verificação (e, só para `nao_publicado`, do início do detalhe) enquanto `metadata.fontes_verificacoes` não tem
-- coluna de tipo (ADR 0053, item 3). A evidência é a primeira verificação (`id_verificacao`) e a captura vigente
-- quando a ocorrência começou (a última feita até então; vazia se nunca houve).
with verificacoes as (

    select
        *,
        case
            when verificacao = 'availability' and resultado = 'error' and detalhe like 'ainda não publicado%' then 'nao_publicado'
            when verificacao = 'availability' and resultado = 'error' then 'indisponivel'
            when verificacao = 'bloqueio' and resultado = 'error' then 'bloqueio'
            when verificacao = 'integridade' and resultado = 'error' then 'arquivo_invalido'
            when verificacao = 'schema_mudou' and resultado = 'warn' then 'mudanca_esquema'
            when verificacao = 'schema' and resultado in ('warn', 'error') then 'coluna_ausente'
            when verificacao = 'volume' and resultado in ('warn', 'error') then 'queda_volume'
        end as tipo_ocorrencia,
        -- conta os "ok" até aqui: linhas com o mesmo número, sem "ok" no meio, são a mesma ocorrência
        sum(case when resultado = 'ok' then 1 else 0 end) over (
            partition by fonte, dataset, particao, verificacao order by dt_verificacao, id_verificacao
        ) as sequencia,
        max(dt_verificacao) over (partition by fonte, dataset, particao, verificacao) as dt_ultima_verificacao

    from {{ ref('stg_metadata__fontes_verificacoes') }}

),

ocorrencias as (

    select
        fonte,
        min(id_verificacao) as id_verificacao,
        dataset,
        particao,
        tipo_ocorrencia,
        min(dt_verificacao) as dt_primeira_observacao,
        max(dt_verificacao) as dt_ultima_observacao,
        count(*) as qtd_observacoes,
        max(dt_verificacao) = max(dt_ultima_verificacao) as fl_em_aberto,
        arg_min(detalhe, id_verificacao) as detalhe

    from verificacoes

    where tipo_ocorrencia is not null

    group by fonte, dataset, particao, verificacao, sequencia, tipo_ocorrencia

)

select
    o.fonte,
    o.id_verificacao,
    o.dataset,
    o.particao,
    o.tipo_ocorrencia,
    o.dt_primeira_observacao,
    o.dt_ultima_observacao,
    o.qtd_observacoes,
    o.fl_em_aberto,
    o.detalhe,
    c.id_captura,
    cast(c.dt_captura as date) as dt_captura

from ocorrencias as o

left join {{ ref('stg_metadata__capturas') }} as c
    on c.fonte = o.fonte
    and c.dataset = o.dataset
    and c.particao is not distinct from o.particao
    and c.dt_captura <= o.dt_primeira_observacao

qualify row_number() over (partition by o.id_verificacao order by c.dt_captura desc nulls last, c.id_captura desc) = 1
