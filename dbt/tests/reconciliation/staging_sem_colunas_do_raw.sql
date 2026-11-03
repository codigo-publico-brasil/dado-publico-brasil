-- O staging de fonte é a base tratada: expõe todos os campos que o raw traz (ADR 0035). Uma coluna do raw conta como
-- exposta quando o nome aparece no SQL de algum staging que lê a tabela, fora de `where` e `qualify` (renomeada ou
-- transformada). Fica de fora só com justificativa em `meta.colunas_omitidas` (coluna: motivo) do modelo que lê a tabela.
-- Colunas técnicas do dlt (`_...`) não contam. Devolve uma linha por coluna do raw que não aparece em nenhum staging.
{%- set tabelas = {} -%}
{%- set codigos = {} -%}
{%- set omitidas = {} -%}
{%- for no in (graph.nodes.values() if execute else []) if no.resource_type == 'model' and no.package_name == project_name and no.fqn[1] == 'staging' and no.fqn[2] not in ('identity', 'metadata') -%}
    {%- set linhas_sql = [] -%}
    {%- for linha in no.raw_code.split('\n') if not modules.re.match('^[ ]*(where|qualify)[ ]', linha) -%}
        {%- do linhas_sql.append(linha) -%}
    {%- endfor -%}
    {%- for dep in no.depends_on.nodes if dep.startswith('source.') -%}
        {%- do tabelas.update({dep: graph.sources[dep]}) -%}
        {%- do codigos.update({dep: codigos.get(dep, '') ~ '\n' ~ (linhas_sql | join('\n'))}) -%}
        {%- do omitidas.update({dep: (omitidas.get(dep, []) + (no.meta.get('colunas_omitidas') or {}).keys() | list)}) -%}
    {%- endfor -%}
{%- endfor -%}
{%- set linhas = [] -%}
{%- for dep, fonte in tabelas.items() -%}
    {%- set relacao = adapter.get_relation(database=fonte.database, schema=fonte.schema, identifier=fonte.identifier) -%}
    {%- if relacao is not none -%}
        {%- for coluna in adapter.get_columns_in_relation(relacao) if not coluna.name.startswith('_') -%}
            {%- if not modules.re.search('(?<![A-Za-z0-9_])' ~ coluna.name ~ '(?![A-Za-z0-9_])', codigos[dep]) and coluna.name not in omitidas[dep] -%}
                {%- do linhas.append("('" ~ fonte.identifier ~ "', '" ~ coluna.name ~ "')") -%}
            {%- endif -%}
        {%- endfor -%}
    {%- endif -%}
{%- endfor %}

select tabela_raw, coluna_raw

from (values {{ linhas | join(', ') if linhas else "('', '')" }}) as e(tabela_raw, coluna_raw)

where tabela_raw <> ''
