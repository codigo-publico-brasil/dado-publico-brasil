{#
    Regras de padronização de texto, como funções (macros) nativas do DuckDB, criadas no início de
    cada execução do dbt (on-run-start). SQL puro: sem código Python por linha.

    Regra geral: só se altera texto 100% maiúsculo ou 100% minúsculo. Texto com as duas caixas foi
    escrito assim pela fonte e fica como está (só com os espaços arrumados). A coluna original nunca
    é substituída: a padronizada é uma coluna a mais. Testes: unit_tests dos modelos de staging e de marts.

    clean_text(x)                  espaços repetidos viram um e as pontas são aparadas
    sentence_case(x)               caixa de frase: "COMISSÃO PERMANENTE" -> "Comissão permanente"
    proper_name(x)                 "MARIA APARECIDA DA SILVA SOUZA" -> "Maria Aparecida da Silva Souza"
                                   (partículas em minúsculas; algarismos romanos e siglas sem vogal, como XYZ,
                                   em maiúsculas)
    standardize_summary(x, siglas) caixa de frase para ementas, mantendo em maiúsculas as palavras de `siglas`
    name_key(x)                    chave para comparar nomes entre fontes: sem acento, minúsculas e espaços únicos
    mascarar_cpf(x)                CPF de terceiros viram ***.nnn.nnn-** (como o Portal da Transparência mascara): pontuado
                                   nnn.nnn.nnn-nn, com ou sem rótulo, e 11 dígitos depois do rótulo "CPF"
    mascarar_dado_pessoal(x, modo) todos os modos aplicam mascarar_cpf; 'favorecido' mascara também 11 dígitos soltos
                                   (CNPJ de 14 fica). Agência e conta bancária NÃO são mascaradas: a fonte oficial as publica
                                   e o dado pessoal que ela publica vem como está (ADR 0050; CPF e documentos seguem a ADR 0017)
    tse_value(x)                   vazio no lugar dos marcadores do TSE (#NULO, #NULO#, #NE, #NE#); nomes que começam
                                   com # (como uma coligação #JUNTOS) são valores legítimos e ficam
#}
{% macro create_text_functions() %}
create or replace macro clean_text(x) as trim(regexp_replace(x, '\s+', ' ', 'g'));

create or replace macro tse_value(x) as
    case when clean_text(x) in ('#NULO', '#NULO#', '#NE', '#NE#') then null else nullif(clean_text(x), '') end;

create or replace macro mascarar_cpf(x) as
    regexp_replace(
        regexp_replace(x, '(C\.?P\.?F[^0-9]{0,8})[0-9]{3,4}\.?([0-9]{3})\.?([0-9]{3})-?[0-9]{2}([^0-9]|$)', '\1***.\2.\3-**\4', 'ig'),
        '(^|[^0-9.])[0-9]{3}\.([0-9]{3})\.([0-9]{3})-[0-9]{2}', '\1***.\2.\3-**', 'g');

create or replace macro mascarar_dado_pessoal(x, modo) as
    case modo
        when 'cpf' then mascarar_cpf(x)
        else regexp_replace(mascarar_cpf(x), '(^|[^0-9])[0-9]{3}([0-9]{3})([0-9]{3})[0-9]{2}($|[^0-9])', '\1***.\2.\3-**\4', 'g')
    end;

create or replace macro name_key(x) as nullif(lower(strip_accents(clean_text(x))), '');

create or replace macro is_single_case(x) as (x = upper(x) or x = lower(x));

create or replace macro sentence_case(x) as
    case
        when x is null or clean_text(x) = '' then null
        when not is_single_case(clean_text(x)) then clean_text(x)
        else upper(clean_text(x)[1]) || lower(clean_text(x)[2:])
    end;

create or replace macro proper_name(x) as
    case
        when x is null or clean_text(x) = '' then null
        when not is_single_case(clean_text(x)) then clean_text(x)
        else array_to_string(
            list_transform(
                regexp_extract_all(clean_text(x), '\p{L}+|[^\p{L}]+'),
                lambda t, i: case
                    when not regexp_matches(t, '^\p{L}+$') then t
                    when upper(t) in ('II', 'III', 'IV', 'VI', 'VII', 'VIII', 'IX', 'X') then upper(t)
                    when length(t) <= 3 and not regexp_matches(upper(t), '[AEIOUÁÀÂÃÉÊÍÓÔÕÚ]') then upper(t)
                    when i > 1 and lower(t) in ('da', 'de', 'do', 'das', 'dos', 'e', 'di', 'du', 'del', 'della', 'von', 'van', 'der') then lower(t)
                    else upper(t[1]) || lower(t[2:])
                end
            ),
            ''
        )
    end;

create or replace macro standardize_summary(x, siglas) as
    case
        when x is null or clean_text(x) = '' then null
        when not is_single_case(clean_text(x)) then clean_text(x)
        else array_to_string(
            list_transform(
                regexp_extract_all(clean_text(x), '\p{L}+|[^\p{L}]+'),
                lambda t, i: case
                    when not regexp_matches(t, '^\p{L}+$') then t
                    when list_contains(siglas, t) and t = upper(t) then t
                    when i = 1 then upper(t[1]) || lower(t[2:])
                    when regexp_matches(
                        regexp_extract_all(clean_text(x), '\p{L}+|[^\p{L}]+')[i - 1], '[.!?]\s+$'
                    ) then upper(t[1]) || lower(t[2:])
                    else lower(t)
                end
            ),
            ''
        )
    end;
{% endmacro %}
