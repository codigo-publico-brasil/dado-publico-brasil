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
    mascarar_dado_pessoal(x, modo) todos os modos aplicam mascarar_cpf; 'bem' mascara também agência e conta bancária
                                   (*****) só quando o número é inequívoco (regras abaixo, em mascarar_conta); ano, cilindrada,
                                   placa e número com menos de 4 dígitos ficam; 'favorecido' mascara também 11 dígitos
                                   soltos (CNPJ de 14 fica)
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

-- Agência e conta bancária (modo 'bem'). Só vira ***** o número inequívoco; na dúvida o texto fica como está
-- (o ano de um veículo, "AP 1234", "125 CC 2008" ou a placa "AGN 1234" não são conta).
--   conta (conta, cta, c/c, c.c., c/p, cc): número com 5 dígitos ou mais, ou com hífen e dígito verificador (nnn-d),
--     ou em grupos (nnnn nnn nnn-d); nnnn-d vale também com até 40 caracteres sem dígito depois do rótulo. Quatro dígitos soltos só se a descrição fala de banco e não parecem ano (19xx/20xx)
--   agência (agência, ag): o mesmo, mais 4 dígitos que não pareçam ano, e o número de 5 dígitos ou com dígito
--     verificador que vem logo depois dela (a conta)
--   se a mesma descrição tem "ag nnnn" e "conta nnnn", 4 dígitos ou mais depois de qualquer rótulo são mascarados
-- Aplicada duas vezes, porque um número
-- colado na palavra seguinte ("AG 1234CONTA 5678") só casa depois da primeira máscara.
create or replace macro re_conta_fill() as
    '(?:[\s.:,\-]|\*+/?|n[º°o]?\.?|nr|corr(?:ente)?|poupan[çc]a|banc[áa]ria|antiga|universal|n[uú]mero|caixa|capital|cef|bb|ita[uú]|bradesco|santander|sicredi|sicoob|banrisul|banco|do|brasil|de|na|hsbc|citibank|safra|ouro|nova|titulo)*';

-- "ag" sozinho aceita só separadores antes do número ("AGN 1234" é placa)
-- "ag" e "cc" sozinhos aceitam só separadores antes do número ("AGN 1234" é placa, "CCN 1234" é motor)
create or replace macro re_ag_rotulo() as 'ag[êe]ncia' || re_conta_fill() || '|ag[\s.:,\-]*';

create or replace macro re_conta_rotulo() as '(?:conta|cta|c/c|c\.c\.|c/p|c/corrente)' || re_conta_fill() || '|cc[\s.:,\-]*';

create or replace macro re_conta_num() as
    '(?:[0-9]+-)*(?:[0-9]{3,}|[0-9]{1,3}(?:\.[0-9]{3})+)[0-9./]*(?:-[0-9xX.]+)+(?:/[0-9xX.\-]+)?|[0-9]{1,4}(?:[\s.][0-9]{2,}){1,}-[0-9xX]|[0-9]{5,}[0-9.\-xX]*';

create or replace macro re_quatro_digitos() as '(?:[013-9][0-9]{3}|1[0-8][0-9]{2}|2[1-9][0-9]{2})';

create or replace macro re_banco() as '(banc|caixa|cef|bradesco|ita[uú]|santander|sicredi|sicoob|banrisul|cresol|coop|ag[êe]ncia|poupan|saldo|corrente|\bbb\b|\bag\b)';

create or replace macro mascarar_agencia(x) as
    regexp_replace(x,
        '(^|[^[:alpha:]])(' || re_ag_rotulo() || ')('
            || re_conta_num() || '|' || re_quatro_digitos() || '(?:-[0-9xX])?(?:[\s,;/\-]+(?:[0-9]{4,}-[0-9xX]|[0-9]{5,}))?)',
        '\1\2*****', 'ig');

-- "cc" também não vale colado em letra ou dígito (final de chassi, cilindrada "125CC")
create or replace macro mascarar_rotulo_conta(x, num) as
    regexp_replace(
        regexp_replace(
            regexp_replace(x, '(^|[^[:alpha:]])((?:conta|cta|c/c|c\.c\.|c/p|c/corrente)' || re_conta_fill() || ')(' || num || ')', '\1\2*****', 'ig'),
            '(^|[^[:alnum:]])(cc[\s.:,\-]*)(' || num || ')', '\1\2*****', 'ig'),
        '(^|[^[:alpha:]])((?:conta|cta|c/c|c\.c\.|c/p)[^0-9]{0,40}?)([0-9.]*[0-9]{4,}-[0-9xX])([^0-9]|$)', '\1\2*****\4', 'ig');

create or replace macro mascarar_conta_uma_vez(x) as mascarar_agencia(mascarar_rotulo_conta(x, re_conta_num()));

create or replace macro mascarar_conta_banco_uma_vez(x) as
    mascarar_agencia(mascarar_rotulo_conta(x, re_conta_num() || '|' || re_quatro_digitos()));

create or replace macro mascarar_conta_par_uma_vez(x) as
    regexp_replace(x,
        '(^|[^[:alpha:]])(' || re_ag_rotulo() || '|' || re_conta_rotulo() || ')'
            || '([0-9][0-9.]*(?:-[0-9xX.]+)+(?:/[0-9xX.\-]+)?|[0-9]{4,}[0-9.\-xX]*)',
        '\1\2*****', 'ig');

create or replace macro mascarar_conta(x) as
    case
        when regexp_matches(x, '(^|[^[:alnum:]])(' || re_ag_rotulo() || ')[0-9]{4}', 'i')
         and regexp_matches(x, '(^|[^[:alpha:]])(' || re_conta_rotulo() || ')[0-9]{4}', 'i')
            then mascarar_conta_par_uma_vez(mascarar_conta_par_uma_vez(x))
        when regexp_matches(x, re_banco(), 'i') then mascarar_conta_banco_uma_vez(mascarar_conta_banco_uma_vez(x))
        else mascarar_conta_uma_vez(mascarar_conta_uma_vez(x))
    end;

create or replace macro mascarar_dado_pessoal(x, modo) as
    case modo
        when 'cpf' then mascarar_cpf(x)
        when 'bem' then mascarar_conta(mascarar_cpf(x))
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
