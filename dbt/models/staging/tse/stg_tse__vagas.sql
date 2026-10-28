-- Vagas de cada cargo em cada unidade eleitoral: uma linha por eleição, cargo e unidade. É o que diz quantas vagas existem,
-- para saber se alguma ficou sem eleito. O arquivo traz também as eleições suplementares (por exemplo, a de governador de
-- Roraima, que vem no arquivo de 2022): elas ficam aqui, identificadas por `eleicao`.
select
    try_cast(ano_eleicao as integer) as ano_eleicao,
    try_cast(cd_eleicao as integer) as cd_eleicao,
    ds_eleicao as eleicao,
    sg_ue as ue,
    proper_name(nm_ue) as ue_nome,
    sg_uf as uf,
    try_cast(cd_cargo as integer) as cd_cargo,
    sentence_case(lower(ds_cargo)) as cargo,
    try_cast(qt_vaga as integer) as qtd_vagas,
    try_strptime(dt_posse, '%d/%m/%Y')::date as dt_posse,
    _source_file_id as id_captura

from {{ tse_source('vagas') }}
