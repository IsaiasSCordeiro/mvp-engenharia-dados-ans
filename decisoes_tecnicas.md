# Decisões Técnicas — registro de arquitetura e pipeline

**MVP Engenharia de Dados | PUC-Rio | Plataforma: Databricks Free Edition**

Documento de trabalho. Alimenta a seção *Pipeline de Dados (Etapa 4.4)* do
README final.

Distinção adotada: **achado de qualidade** é constatação sobre o dado — outra
pessoa, com a mesma fonte, chegaria à mesma conclusão. **Decisão técnica** é
escolha de implementação — poderia ter sido feita de outro modo, e por isso
exige justificativa.

---

## DT-01 — Plataforma: Databricks Free Edition

**Alternativas:** AWS, GCP, Azure nativos.

**Escolha:** Databricks Free Edition.

**Justificativa:** concentra armazenamento, processamento, catálogo e notebooks
em um único ambiente, sem necessidade de integrar serviços separados nem
configurar provedor de nuvem. Não exige cartão de crédito. É a plataforma com
suporte do curso.

**Revisão da justificativa durante a execução:** a avaliação inicial era de que
o volume não justificaria processamento distribuído — as bases do SIP somam
cerca de 160 mil linhas. A medição da base de beneficiários alterou esse
diagnóstico: uma única UF (Minas Gerais) resultou em 9.089.448 linhas e 11,4 GB
em memória, inviabilizando processamento em máquina local. A escolha da nuvem
deixou de ser requisito acadêmico e passou a ser necessidade técnica
comprovada.

---

## DT-02 — Arquitetura em camadas (medalhão)

**Escolha:** três schemas — `bronze`, `silver`, `gold`.

**Justificativa:** separação física das camadas torna explícita a progressão
dado bruto → dado limpo → dado modelado. Permite auditar qualquer resultado
retrocedendo até a evidência original.

**Implementação:** cada camada é um schema no Unity Catalog, com `COMMENT`
descritivo gravado no próprio catálogo.

---

## DT-03 — Bronze sem agregação

**Alternativa considerada:** agregar durante a ingestão para contornar a
restrição de memória da base de beneficiários.

**Escolha:** rejeitada. A camada bronze preserva a estrutura original da fonte.

**Justificativa:** agregar na ingestão altera a estrutura dos dados de origem e
elimina a rastreabilidade — a bronze deixaria de ser evidência e passaria a ser
derivação, impossibilitando auditoria do que a fonte efetivamente entregou.

**Solução adotada para o volume:** limitação de escopo por unidade federativa,
com ingestão integral das UFs selecionadas e preservação das 27 colunas
originais. O recorte territorial é critério de negócio declarado, não corte
arbitrário de linhas — a leitura por `nrows` foi descartada porque o arquivo
pode vir ordenado, o que produziria amostra enviesada.

---

## DT-04 — Tipagem postergada para a silver

**Escolha:** leitura com `dtype=str` (pandas) e `inferSchema=False` (Spark) na
camada bronze. Nenhuma conversão de tipo na ingestão.

**Justificativa:** conversão é interpretação, e interpretação é
responsabilidade da silver. Falhas de conversão ficam visíveis e tratáveis na
camada correta, em vez de ocorrerem silenciosamente na ingestão.

**Impacto direto:** preserva zeros à esquerda em códigos de tamanho fixo —
`"000515"` permanece texto em vez de ser convertido para o inteiro `515`, o que
quebraria joins sem gerar erro.

---

## DT-05 — Encoding definido por base

**Escolha:** `utf-8` para o SIP, `latin-1` para o cadastro de operadoras.

**Justificativa:** a ANS não adota encoding único no portal. A convenção
inicial de `latin-1` para dados abertos brasileiros produziu corrupção de
acentuação no SIP. O parâmetro passou a ser determinado por inspeção de cada
base, não por convenção global.

---

## DT-06 — Metadados de controle na ingestão

**Escolha:** acréscimo de `_arquivo_origem` e `_data_ingestao` a toda tabela
bronze.

**Justificativa:** rastreabilidade de origem e auditoria temporal. Com 24
arquivos trimestrais empilhados na mesma tabela, `_arquivo_origem` é o que
permite identificar a procedência de cada registro. `_data_ingestao` viabiliza
deduplicação de retificações, mantendo a versão mais recente.

**Observação:** o prefixo `_` distingue colunas de controle das colunas de
negócio originais da fonte.

---

## DT-07 — Modo de escrita idempotente

**Escolha:** `mode("overwrite")` nas cargas.

**Alternativa:** `mode("append")`.

**Justificativa:** o notebook será executado por terceiros durante a avaliação.
Com `append`, cada reexecução duplicaria os dados. Com `overwrite`, o resultado
é idêntico independentemente do número de execuções — propriedade de
idempotência, desejável em qualquer pipeline reprodutível.

---

## DT-08 — Linguagens: SQL e Python no mesmo pipeline

**Escolha:** SQL para DDL e consultas; Python para ingestão e transformação.

**Justificativa:** SQL não acessa URLs externas nem manipula arquivos
compactados. Python resolve a coleta; SQL expressa criação de schema,
comentários de catálogo e consultas analíticas de forma mais direta e legível
do que o equivalente em `spark.sql("...")` embutido em strings.

**Implementação:** o comando mágico `%sql` alterna a linguagem por célula.

---

## DT-09 — Ramificação dos notebooks

**Escolha:** um notebook por etapa do pipeline.

| Notebook | Responsabilidade |
|---|---|
| `00_exploracao` | Inspeção das fontes; não integra o pipeline |
| `01_bronze_ingestao` | Coleta e persistência do dado bruto |
| `02_silver_transformacao` | Limpeza, tipagem e enriquecimento |
| `03_gold_modelagem` | Construção de fatos e dimensões |
| `04_analise` | Qualidade de dados e respostas às perguntas |

**Justificativa:** isola falhas, permite reexecutar uma etapa sem reprocessar
as anteriores e torna a leitura do repositório autoexplicativa. O notebook de
exploração é mantido no repositório como registro da investigação das fontes,
mas está identificado como não pertencente ao fluxo de produção.

---

## DT-10 — Pandas na leitura, Spark na escrita

**Escolha:** leitura das fontes com pandas; persistência em Delta com Spark.

**Justificativa:** o pandas lê diretamente de URL e trata arquivos compactados
com uma linha de código, o que o Spark não faz nativamente. A escrita em
formato Delta — que fornece transações ACID e é o padrão do Lakehouse — exige
Spark.

**Limite da escolha:** válida enquanto o arquivo couber na memória do driver.
Para a base de beneficiários, cuja UF de maior volume ocupa 11,4 GB, a leitura
ocorre em blocos (`chunksize`) ou diretamente por Spark.

---

## DT-11 — Esquema estrela com dimensões parcialmente conformadas

**Escolha:** múltiplas tabelas fato compartilhando dimensões, quando aplicável.

**Justificativa e limitação declarada:** o SIP não identifica a operadora — os
dados chegam agregados por porte e modalidade. A base de beneficiários
identifica a operadora, mas não registra utilização. As duas fatos compartilham
apenas a dimensão tempo.

Isso significa que perguntas que exijam cruzamento direto entre carteira e
utilização — por exemplo, se operadoras com maior cancelamento apresentam maior
frequência de exames — não são respondíveis com estas fontes. A limitação é
estrutural, decorre do desenho das bases públicas e está documentada no
catálogo de dados para não ser interpretada como falha de modelagem.

---

## DT-12 — Separação em dois fatos por granularidade de medida

**Escolha:** `fato_custo` (nível 1 da hierarquia) e `fato_utilizacao` (níveis 2
e 3), a partir da mesma tabela de origem.

**Justificativa:** despesa e beneficiários expostos são reportados apenas no
nível agregado; quantidade de eventos é reportada no detalhe. Modelar em tabela
única exigiria descartar 80% das linhas ou conviver com medidas
majoritariamente nulas.

**Referência:** ver achado QD-04 no documento de qualidade de dados.

---

## DT-13 — Dimensão derivada de classificação de exames

**Escolha:** criação do atributo `CLASSIF_EXAME` na camada silver, com as
categorias imagem, laboratorial, endoscópico e funcional.

**Justificativa:** a fonte não classifica os exames por natureza diagnóstica,
descendo direto ao procedimento. Sem esse enriquecimento, a pergunta de negócio
sobre exames de imagem versus laboratoriais fica sem resposta.

**Ressalvas declaradas:** a classificação é autoral e não consta da fonte
original; as categorias endoscópico e funcional foram criadas para evitar
enquadramento forçado de procedimentos que não pertencem a nenhuma das duas
categorias de interesse; o critério de atribuição é a descrição do procedimento
e está integralmente documentado no catálogo.

**Validação com o orientador:** a prática foi submetida ao professor
responsável pelo MVP, que confirmou sua adequação desde que a dimensão derivada
seja construída a partir da camada silver, preservando-se a estrutura original
da fonte na camada bronze. A implementação atende integralmente a essa
orientação — `silver.dim_classif_exame` é derivada de `silver.sip`, e
`bronze.sip` mantém as 11 colunas originais sem qualquer transformação.

Essa mesma orientação confirma, por consequência, a decisão registrada em
DT-03: agregação durante a ingestão descaracterizaria a camada bronze.

**Cobertura verificada:** ver QD-14 — os 20 procedimentos classificados, sem
órfãos.

**Escopo da classificação:** aplicada exclusivamente ao nível 2 do item C
(Exames). Os demais grupos assistenciais não receberam classificação derivada,
por não haver pergunta de negócio que a demande.

---

## DT-14 — Fixação do catálogo corrente

**Escolha:** declaração de `USE CATALOG workspace` no início de cada notebook.

**Justificativa:** o Unity Catalog opera em três níveis —
catálogo, schema, tabela. Sem fixação explícita, comandos DDL podem resolver
para o catálogo `default` e falhar com erro de tabela não encontrada, ainda que
a tabela exista. A fixação elimina a ambiguidade e torna o notebook executável
por terceiros sem configuração prévia.

---

## DT-15 — Validações por camada

**Alternativa:** concentrar toda a verificação de qualidade em etapa única ao
final do pipeline.

**Escolha:** cada notebook encerra com uma seção de validação da camada que
produziu.

**Justificativa:** falha detectada na camada de origem evita reprocessamento de
todas as etapas seguintes. O princípio equivale ao controle de qualidade em
posto de trabalho, oposto à inspeção final.

**Implementação:** as saídas das validações permanecem visíveis nos notebooks
entregues, constituindo a evidência de execução exigida pelo enunciado.

---

## DT-16 — Empilhamento das competências em tabela única

**Alternativa:** uma tabela por competência, totalizando 24 objetos.

**Escolha:** tabela única `bronze.sip` com as 24 competências empilhadas.

**Justificativa:** viabilizado pela estabilidade de esquema verificada (QD-07)
e de domínio (QD-08). A coluna `_arquivo_origem` preserva a procedência de cada
registro, mantendo a rastreabilidade que a alternativa ofereceria. A opção por
24 tabelas exigiria `UNION` explícito em toda consulta temporal e poluiria o
catálogo sem ganho analítico.

**Resultado:** 156.792 registros, com contagens por arquivo idênticas às da
fonte (QD-10).

---

## DT-17 — Chaves substitutas nas dimensões

**Escolha:** utilização dos próprios códigos naturais como chave
(`ID_TRIMESTRE` em `dim_tempo`, `ID_ITEM_ASST` em `dim_evento`) e chave
composta concatenada em `dim_perfil_operadora`.

**Alternativa:** geração de chaves sequenciais artificiais.

**Justificativa:** os códigos naturais da fonte são estáveis e verificadamente
únicos (QD-15). Chaves sequenciais acrescentariam uma etapa de junção sem
benefício, dado que não há necessidade de historização de dimensão (SCD tipo 2)
— os atributos de perfil descrevem a combinação, não uma entidade que evolui no
tempo.

**Exceção:** `dim_perfil_operadora` não possui código natural, pois deriva da
combinação de quatro atributos degenerados presentes na tabela de origem. Nesse
caso, a chave é a concatenação dos quatro valores.

---

## DT-18 — Escopo hierárquico do fato de utilização

**Escolha:** `fato_utilizacao` carrega os níveis 2, 3 e 4, totalizando 145.338
registros.

**Justificativa:** o nível 4 contém detalhamento clínico específico —
tratamentos oncológicos, acidente vascular cerebral, internação em UTI neonatal
— e representa 7.350 registros. Sua exclusão ocorreria por omissão, não por
critério. A inclusão não distorce agregações, uma vez que toda consulta ao fato
filtra explicitamente o nível analisado.

**Exclusão deliberada:** o nível 1 permanece fora deste fato por pertencer a
`fato_custo`. Carregar ambos produziria dupla contagem entre o total e seus
componentes.

---

## DT-19 — Dupla granularidade de grupo na dimensão de evento

**Escolha:** `dim_evento` expõe `CD_GRUPO`, obtido pelo primeiro caractere do
identificador.

**Alternativa considerada:** `split(ID_ITEM_ASST, '.')[0]`, que retornaria o
texto até o primeiro ponto.

**Diferença prática:** a distinção só importa no grupo E, onde a fonte registra
E, E1 e E2 como códigos distintos. A escolha atual trata internações como bloco
único; a alternativa preservaria a separação entre internação, tipo de
internação e regime de internação.

**Justificativa:** as perguntas de negócio tratam internação como categoria
única. A granularidade adicional permanece acessível via `ID_ITEM_ASST`, sem
necessidade de coluna dedicada.

---

## DT-20 — Cálculo de medidas não aditivas

**Escolha:** taxas e razões — frequência de utilização, custo médio por evento,
custo por beneficiário — são calculadas somando numerador e denominador antes
da divisão.

**Alternativa rejeitada:** média das razões individuais.

**Justificativa:** a média de razões atribui peso idêntico a grupos de tamanhos
distintos, distorcendo o resultado em favor de combinações de baixa
representatividade. Uma combinação com 500 beneficiários pesaria tanto quanto
uma com 5 milhões.

**Consequência para o modelo:** essas medidas são recalculadas a cada nível de
agregação e nunca somadas. A propriedade está registrada no catálogo de dados
para evitar uso indevido em ferramentas de visualização.

---

## DT-21 — Agregação anual nas séries temporais

**Escolha:** as análises de evolução adotam agregação anual, não trimestral.

**Justificativa:** o denominador de exposição acumula quatro competências por
ano, mas o fator é constante em toda a série, preservando a comparabilidade
entre anos. A agregação anual também neutraliza a variação sazonal intra-ano,
isolando a tendência — comparar o primeiro com o quarto trimestre confundiria
sazonalidade com evolução.

---

## DT-22 — Tratamento do ano de 2020 nas comparações

**Escolha:** o ano de 2020 é tratado como base atípica.

**Justificativa:** a série inicia no primeiro ano da pandemia de COVID-19,
quando houve adiamento generalizado de procedimentos eletivos. A frequência de
utilização de exames salta 25% entre 2020 e 2021 e estabiliza a partir de 2022,
padrão compatível com recuperação de demanda represada.

**Implementação:** comparações de crescimento adotam 2021 ou 2022 como base. A
variação entre 2020 e 2021 é interpretada como recuperação, não como
tendência estrutural.

---

## DT-23 — Escopo restrito a uma única fonte

**Alternativa considerada:** incorporar a base de beneficiários (SIB) ao
modelo, ampliando o escopo para participação de mercado, perfil demográfico e
permanência.

**Escolha:** manter o escopo restrito ao SIP.

**Justificativa:** as duas bases não compartilham chave além da dimensão
temporal — o SIP não identifica operadoras individualmente e o SIB não registra
utilização. A incorporação produziria dois fatos desconectados, incapazes de
responder qualquer pergunta que exigisse cruzamento entre carteira e uso.

Some-se o volume: uma única unidade federativa da base de beneficiários resultou
em 9.089.448 registros e 11,4 GB em memória, exigindo estratégia de ingestão em
blocos para 27 arquivos.

**Consequência assumida:** as perguntas 1 e 2 permanecem sem resposta. A decisão
priorizou a profundidade da análise sobre a amplitude do escopo, e está
declarada na Autoavaliação.

---

## DT-24 — Notebook único para o fluxo de produção

**Alternativa considerada:** ramificação em um notebook por camada.

**Escolha:** notebook único, estruturado em onze seções que acompanham as
camadas da arquitetura, mais um notebook separado de exploração fora do fluxo.

**Justificativa:** a opção por arquivo único é adequada ao escopo deste
trabalho — desenvolvimento individual, volume que permite reexecução completa em
poucos minutos e avaliação por leitura sequencial.

**Reconhecimento do padrão de mercado:** em ambiente produtivo a ramificação
seria preferível, por permitir reexecução isolada de cada etapa, orquestração
com retry independente e edição concorrente por múltiplos desenvolvedores. A
decisão é de escopo, não de desconhecimento da prática.

---

## DT-25 — Manutenção do notebook de exploração no repositório

**Escolha:** `00_exploracao` é versionado junto ao pipeline, identificado como
fora do fluxo de produção.

**Justificativa:** registra a investigação que fundamentou as decisões de
modelagem — inspeção de encoding, descoberta da hierarquia, verificação de
estabilidade de esquema e de domínio. Sem ele, as decisões documentadas neste
arquivo apareceriam sem a evidência que as originou.

**Delimitação:** o notebook não é executado como parte do pipeline e não produz
nenhuma tabela consumida pelas camadas seguintes.

---

## Síntese das decisões

| Categoria | Decisões |
|---|---|
| Plataforma e arquitetura | DT-01, DT-02, DT-14, DT-24, DT-25 |
| Fidelidade à fonte | DT-03, DT-04, DT-05, DT-06 |
| Reprodutibilidade | DT-07, DT-08, DT-15, DT-16 |
| Modelagem dimensional | DT-11, DT-12, DT-17, DT-18, DT-19, DT-23 |
| Tratamento de medidas | DT-10, DT-13, DT-20, DT-21, DT-22 |

Nenhuma decisão permanece em aberto.

---

## Orientações recebidas do professor

| Tema | Orientação | Efeito |
|---|---|---|
| Agregação na ingestão | Descaracteriza a camada bronze, pois altera a estrutura da fonte. Para questões de volume, limitar em linhas sem mexer na estrutura | Confirma DT-03 |
| Dimensão derivada | Permitida, desde que construída a partir da camada silver. A bronze deve respeitar a estrutura inicial da fonte | Confirma DT-13 |
