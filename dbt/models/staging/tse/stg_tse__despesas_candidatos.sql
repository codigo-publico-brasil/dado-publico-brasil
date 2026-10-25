-- Despesas contratadas pelos candidatos (todos os cargos): uma linha por despesa. O valor é o declarado.
-- A carga é pesada e opcional: enquanto ela não vier, esta tabela fica vazia (ver o macro raw_or_empty).
select
    try_cast(aa_eleicao as integer) as ano_eleicao,
    try_cast(st_turno as integer) as turno,
    aa_eleicao || ':' || sg_ue || ':' || sq_candidato as id_candidatura,
    try_cast(sq_candidato as bigint) as sq_candidato,
    try_cast(sq_prestador_contas as bigint) as sq_prestador_contas,
    try_cast(sq_despesa as bigint) as sq_despesa,
    sg_ue as ue,
    sg_uf as uf,
    sentence_case(lower(ds_cargo)) as cargo,
    sentence_case(tp_prestacao_contas) as tipo_prestacao,
    try_strptime(dt_prestacao_contas, '%d/%m/%Y')::date as dt_prestacao,
    try_strptime(dt_despesa, '%d/%m/%Y')::date as dt_despesa,
    try_cast(replace(vr_despesa_contratada, ',', '.') as decimal(18, 2)) as valor,
    _source_file_id as id_captura

from {{ raw_or_empty('tse', 'despesas_candidatos', ['aa_eleicao', 'st_turno', 'tp_prestacao_contas', 'dt_prestacao_contas', 'sq_prestador_contas', 'sg_uf', 'sg_ue', 'ds_cargo', 'sq_candidato', 'sq_despesa', 'dt_despesa', 'vr_despesa_contratada']) }}
