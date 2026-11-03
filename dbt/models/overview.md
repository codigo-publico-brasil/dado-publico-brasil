{% docs __overview__ %}

# Dado Público Brasil: tabelas e colunas

Esta é a documentação de cada tabela do lake público: o que significa, de qual fonte oficial vem, como foi derivada e como cada coluna é descrita. Os dados em si estão em Parquet, no mesmo endereço, e cada linha pode ser conferida até o arquivo original da fonte.

- [Página inicial do lake](/) — catálogo para consultar, manifesto e guia de uso.
- [Qualidade dos dados](/docs/qualidade.html) — resultado dos testes, volume e frescor a cada carga.

### Como navegar

- A aba **Project** mostra as tabelas na ordem em que são construídas: `staging` (a base tratada de cada fonte), `intermediate` (passos da derivação) e `marts` (o que se consome).
- A aba **Database** mostra as mesmas tabelas agrupadas por esquema.
- Em cada tabela, o grafo de linhagem mostra de onde vêm os dados.

O Dado Público Brasil é um projeto do Código Público Brasil. Este site é gerado com o [dbt](https://www.getdbt.com/) a cada publicação.

{% enddocs %}
