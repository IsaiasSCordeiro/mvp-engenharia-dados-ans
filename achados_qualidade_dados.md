# Achados de Qualidade de Dados — registro de evidências

**MVP Engenharia de Dados | PUC-Rio | Fonte: ANS — Portal de Dados Abertos**

Documento de trabalho. Alimenta a seção *Qualidade de Dados (Etapa 4.5)* do
README final. Cada achado registra sintoma, investigação, causa e tratamento.

---

## QD-01 — Encoding divergente entre bases

**Sintoma:** descrições exibidas com caracteres corrompidos
(`CONSULTAS MÃ□DICAS`, `MÃ□DICO-HOSPITALAR`).

**Investigação:** leitura inicial adotou `encoding="latin-1"`, padrão comum em
dados abertos brasileiros. Teste com `encoding="utf-8"` restaurou a acentuação.

**Causa:** os arquivos do SIP são publicados em UTF-8, enquanto outras bases da
ANS (ex.: cadastro de operadoras) utilizam ISO-8859-1. Não há padrão único de
encoding no portal.

**Tratamento:** encoding definido por base, não por convenção global. SIP lido
com `utf-8`.

**Impacto:** sem correção, todas as descrições de itens assistenciais e
modalidades ficariam ilegíveis nas dimensões do modelo.

---

## QD-02 — Zeros à esquerda em chave de registro

**Sintoma:** risco de falha silenciosa em joins.

**Investigação:** inspeção do cadastro de operadoras revelou registros como
`"000515"` (Allianz Saúde), armazenados como texto com zeros à esquerda.

**Causa:** `REGISTRO_OPERADORA` é código de tamanho fixo. Leitura sem tipagem
explícita converte para inteiro, transformando `"000515"` em `515`.

**Tratamento:** leitura de todas as bases com `dtype=str` (pandas) e
`inferSchema=False` (Spark). Nenhuma conversão de tipo ocorre na camada bronze.

**Impacto:** join entre bases retornaria vazio sem gerar erro — falha silenciosa,
a mais perigosa em pipeline de dados.

---

## QD-03 — Hierarquia embutida no identificador de item

**Sintoma:** somatório de `QT_EVENTOS` superestima o volume real.

**Investigação:** análise do padrão de `ID_ITEM_ASST` identificou estrutura
hierárquica de até quatro níveis, sinalizada por pontos:

```
C          EXAMES                          nível 1
C.02       TOMOGRAFIA COMPUTADORIZADA      nível 2
C.10       MAMOGRAFIA CONVENCIONAL         nível 2
C.10.01    MAMOGRAFIA (50 A 69 ANOS)       nível 3
```

Distribuição em 2024-10: 432 linhas de nível 1, 2.833 de nível 2, 2.362 de
nível 3 e 276 de nível 4.

**Causa:** a tabela contém simultaneamente totais, subtotais e detalhes. O
agregado não é derivado — está registrado como linha própria.

**Tratamento:** criação da coluna `NIVEL` por contagem de separadores
(`ID_ITEM_ASST.str.count(".") + 1`). Toda agregação filtra um único nível.

**Impacto:** sem o filtro, o mesmo evento é contado até três vezes. O erro não
gera exceção — apenas devolve número inflado.

---

## QD-04 — Duas granularidades de medida na mesma tabela

**Sintoma:** 80% de nulos em `QT_BENEF_FORA_CARENCIA` e 88% em
`VL_DESPESA_ASST_LIQ`, contra 0,8% em `QT_EVENTOS`.

**Investigação:** cruzamento dos nulos com o nível hierárquico revelou
progressão monotônica:

| Nível | Linhas | % sem beneficiários | % sem despesa | % sem eventos |
|---|---|---|---|---|
| 1 | 432 | 41,4 | 21,3 | 11,1 |
| 2 | 2.833 | 73,1 | 86,4 | 0,0 |
| 3 | 2.362 | 93,0 | 100,0 | 0,0 |
| 4 | 276 | 100,0 | 100,0 | 0,0 |

**Causa:** despesa e beneficiários expostos são reportados apenas no nível
agregado; a quantidade de eventos é reportada no detalhe. São duas
granularidades de medida convivendo na mesma tabela física.

**Tratamento:** separação em dois fatos com grãos distintos, compartilhando as
mesmas dimensões conformadas — `fato_custo` (nível 1) e `fato_utilizacao`
(níveis 2 e 3).

**Impacto:** modelagem em tabela única exigiria descartar 80% das linhas ou
conviver com medidas majoritariamente vazias.

---

## QD-05 — Nulos residuais de despesa no nível agregado

**Sintoma:** mesmo no nível 1, 21,3% dos registros de cobertura
médico-hospitalar não apresentavam despesa.

**Investigação:** decomposição por cobertura e modalidade mostrou 0% de nulos em
cobertura odontológica e 20,9% a 23,8% em médico-hospitalar, de forma uniforme
entre as cinco modalidades. A uniformidade afastou a hipótese de falha
específica de operadora. Decomposição por item assistencial isolou a causa:

| Item | Descrição | % sem despesa |
|---|---|---|
| E1 | Tipo de internação | 100,0 |
| E2 | Regime de internação | 100,0 |
| A, B, C, D, E, H, I | Demais itens de nível 1 | 0,0 |

**Causa:** `E1` e `E2` são desdobramentos qualitativos de `E` (Internações) —
descrevem como a internação ocorreu, não constituem categoria de gasto própria.
Por definição não possuem despesa associada.

**Tratamento:** exclusão de `E1` e `E2` do `fato_custo`, com manutenção no
`fato_utilizacao`. Após o filtro, a completude da despesa é de 100% nos sete
itens de nível 1.

**Impacto:** achado converte um aparente problema de completude em regra de
negócio documentada.

---

## QD-06 — Ausência de classificação de exames por natureza

**Sintoma:** a pergunta de negócio sobre exames de imagem versus laboratoriais
não encontra campo correspondente na fonte.

**Investigação:** o nível 2 do item `C` (Exames) desce diretamente ao
procedimento — ressonância, tomografia, mamografia, colonoscopia, hemoglobina
glicada — sem agrupamento por natureza.

**Causa:** a ANS não classifica os exames por modalidade diagnóstica.

**Tratamento:** criação de dimensão derivada `CLASSIF_EXAME` na camada silver,
com quatro categorias — imagem, laboratorial, endoscópico e funcional —
atribuídas a partir da descrição do procedimento.

**Ressalvas declaradas:** a classificação é autoral e não consta da fonte
original. As categorias endoscópico e funcional foram criadas para evitar
enquadramento forçado de procedimentos que não são nem imagem nem laboratório.
O SIP contempla apenas os exames monitorados pela ANS, não a totalidade dos
exames realizados.

---

## QD-07 — Estabilidade do esquema ao longo da série histórica

**Sintoma:** risco de *schema drift* na ingestão de 24 arquivos trimestrais
(2020 a 2025).

**Investigação:** comparação da estrutura de colunas em três competências
distribuídas ao longo da série — 2020-01, 2023-01 e 2025-10.

**Resultado:** as 11 colunas são idênticas em nome, quantidade e ordem nas três
competências.

**Tratamento:** ingestão uniforme dos 24 arquivos com um único padrão de leitura,
sem necessidade de mapa de-para entre versões.

**Impacto:** verificação preventiva. A estabilidade estrutural não garante
estabilidade de domínio — a consistência dos valores de `ID_ITEM_ASST` ao longo
da série é objeto de verificação separada.

---

## QD-08 — Estabilidade do domínio ao longo da série

**Sintoma:** risco de incomparabilidade temporal caso itens assistenciais
tenham sido incluídos ou excluídos entre 2020 e 2025.

**Investigação:** comparação do conjunto de itens de nível 1 entre as
competências 2020-01 e 2025-10, seguida de contagem em todas as 24
competências.

**Resultado:** os nove itens (A, B, C, D, E, E1, E2, H, I) estão presentes em
todas as competências, sem inclusões ou exclusões.

**Tratamento:** nenhum necessário. Confirma-se a comparabilidade temporal da
série completa.

**Impacto:** viabiliza as perguntas de sazonalidade e evolução temporal sem
restrição de período.

---

## QD-09 — Volume e integridade da série

**Investigação:** leitura das 24 competências disponíveis (2020-01 a 2025-10),
com registro de volume e contagem de itens de nível 1 por arquivo.

**Resultado:** nenhuma falha de leitura. Volume por competência entre 5.578 e
7.471 registros, com nove itens de nível 1 em todas.

**Observação para a análise:** o volume apresenta tendência de redução ao longo
da série — de 7.471 registros em 2020-01 para 5.578 em 2025-10. A hipótese de
consolidação do setor, com menor número de combinações reportadas, deve ser
investigada na etapa de análise, não sendo tratada aqui como problema de
qualidade.

---

## QD-10 — Volume consolidado após ingestão

**Investigação:** contagem de registros por `_arquivo_origem` em `bronze.sip`
após o empilhamento das 24 competências.

**Resultado:** 156.792 registros distribuídos em 24 arquivos, com contagens
individuais idênticas às obtidas na leitura direta da fonte.

**Tratamento:** nenhum necessário. Confirma-se que o empilhamento não gerou
perda nem duplicação.

---

## QD-11 — Unicidade do grão

**Sintoma:** risco de retificações concorrentes, comum em bases regulatórias
onde operadoras podem reenviar informação.

**Investigação:** comparação entre a contagem total e a contagem de combinações
distintas de porte, modalidade, cobertura, contratação, trimestre e item
assistencial.

**Resultado:** 156.792 registros para 156.792 combinações distintas.

**Tratamento:** deduplicação por `DT_CORTE` na camada silver foi considerada e
descartada por desnecessária.

**Impacto:** simplifica o pipeline e confirma que o grão declarado no catálogo
corresponde ao grão real dos dados.

---

## QD-12 — Formatos numéricos divergentes na mesma tabela

**Sintoma:** risco de conversão numérica falhar silenciosamente.

**Investigação:** inspeção dos valores brutos das colunas de medida.

**Resultado:** duas convenções decimais coexistem na mesma tabela —
`VL_DESPESA_ASST_LIQ` utiliza vírgula (padrão brasileiro, ex.: `275660581,51`)
e `QT_EVENTOS` utiliza ponto (padrão americano, ex.: `40421.0`), esta última
com casa decimal apesar de representar contagem inteira.

**Tratamento:** conversão tratada por coluna na camada silver — substituição de
vírgula por ponto antes do cast em despesa; cast direto para inteiro em
quantidade.

**Impacto:** conversão uniforme produziria nulos silenciosos em uma das duas
colunas, sem gerar erro.

---

## QD-13 — Integridade da conversão de tipos

**Investigação:** comparação da contagem de nulos entre as camadas bronze e
silver, após a tipagem.

**Resultado:**

| Camada | Sem quantidade de eventos | Sem despesa |
|---|---|---|
| Bronze | 1.252 | 137.635 |
| Silver | 1.252 | 137.635 |

**Tratamento:** nenhum necessário. A conversão preservou integralmente o dado
original, sem introduzir nulos.

**Impacto:** valida a transformação mais crítica da camada silver. Divergência
nesses números indicaria valores perdidos na conversão.

---

## QD-14 — Cobertura da classificação derivada de exames

**Investigação:** `LEFT JOIN` entre os procedimentos de nível 2 do item C
presentes em `silver.sip` e a dimensão `silver.dim_classif_exame`, filtrando
registros sem correspondência.

**Resultado:** zero registros órfãos. Os 20 procedimentos receberam
classificação.

**Tratamento:** nenhum necessário.

**Impacto:** item não classificado produziria nulo que se propagaria
silenciosamente até a análise final. A validação é preventiva e seu resultado
vazio constitui evidência de conformidade.

---

## QD-15 — Unicidade das chaves dimensionais

**Investigação:** comparação entre número de linhas e de chaves distintas em
cada dimensão da camada gold.

**Resultado:**

| Dimensão | Linhas | Chaves distintas |
|---|---|---|
| `gold.dim_tempo` | 24 | 24 |
| `gold.dim_evento` | 123 | 123 |
| `gold.dim_perfil_operadora` | 82 | 82 |

**Tratamento:** nenhum necessário. Confirma-se a cardinalidade um-para-muitos
entre dimensões e tabelas fato.

**Observação:** `dim_perfil_operadora` apresenta 82 combinações contra 126
teoricamente possíveis (3 portes × 7 modalidades × 2 coberturas × 3
contratações). As 44 combinações ausentes correspondem a configurações que não
ocorrem no mercado — cooperativa odontológica em cobertura médico-hospitalar,
por exemplo. Trata-se de característica do setor, não de lacuna de dados.

---

## QD-16 — Integridade referencial entre fatos e dimensões

**Investigação:** `LEFT JOIN` de cada tabela fato contra as três dimensões
conformadas, contabilizando chaves sem correspondência.

**Resultado:**

| Fato | Registros | Órfãos em tempo | Órfãos em evento | Órfãos em perfil |
|---|---|---|---|---|
| `fato_custo` | 9.004 | 0 | 0 | 0 |
| `fato_utilizacao` | 137.988 | 0 | 0 | 0 |

**Tratamento:** nenhum necessário. Confirma-se a consistência do esquema
estrela.

*Contagem de `fato_utilizacao` anterior à inclusão do nível 4 — ver QD-17.*

---

## QD-17 — Rastreabilidade da carga entre silver e gold

**Sintoma:** necessidade de justificar a diferença entre o volume da camada
silver e a soma das tabelas fato.

**Investigação:** contagem de registros por nível hierárquico e por sinalização
de item sem despesa.

**Resultado:**

| Origem | Registros | Destino |
|---|---|---|
| Nível 1, com despesa | 9.004 | `fato_custo` |
| Nível 2 | 75.204 | `fato_utilizacao` |
| Nível 3 | 62.784 | `fato_utilizacao` |
| Nível 4 | 7.350 | `fato_utilizacao` |
| Nível 1, itens E1 e E2 | 2.450 | Excluído por regra (QD-05) |

**Tratamento:** os 2.450 registros de E1 e E2 permanecem fora do fato de custo
por não possuírem despesa por definição. Todos os demais foram carregados.

**Impacto:** nenhum registro foi perdido sem justificativa documentada. Total
de 156.792 integralmente rastreado.

---

## QD-18 — Hierarquia incompleta na fonte

**Sintoma:** dois grupos sem registro de nível 1.

**Investigação:** contagem de registros por grupo e nível hierárquico.

**Resultado:** os grupos F (23.275 registros, níveis 2 a 4) e G (1.221
registros, nível 2) não possuem linha de nível 1, ao contrário dos demais (A,
B, C, D, E, H, I). A fonte publica o detalhamento sem o agregado.

**Tratamento:** nenhum tratamento corretivo é possível — o dado não existe na
fonte.

**Impacto:** F e G estão ausentes de `fato_custo`, que carrega apenas o nível
1. Análises de despesa e de custo por beneficiário não cobrem esses grupos —
limitação a declarar nas respostas das perguntas 7 e 8.

---

## QD-19 — Naturezas distintas na mesma coluna

**Sintoma:** os grupos F e G, ao serem inspecionados, não correspondiam a
serviços assistenciais.

**Investigação:** listagem das descrições dos itens dos grupos F e G.

**Resultado:** F registra agravos monitorados — neoplasias, diabetes mellitus,
doenças hipertensivas, insuficiência cardíaca, infarto, acidente vascular
cerebral, doença pulmonar obstrutiva crônica, causas externas. G registra
nascidos vivos. Nenhum dos dois é serviço prestado: são condições de saúde e
desfechos observados na população coberta.

**Causa:** `ID_ITEM_ASST` acomoda duas naturezas distintas — o que a operadora
executou e o que ocorreu com os beneficiários.

**Tratamento:** criação do atributo `TP_NATUREZA` em `gold.dim_evento`,
distinguindo SERVICO de AGRAVO, com filtro explícito em toda análise de
utilização.

**Impacto:** agregar as duas naturezas produziria somatório entre unidades
incomparáveis — consultas realizadas somadas a casos de diabetes.

---

## QD-20 — Distribuição da classificação por natureza

**Investigação:** contagem de itens por `TP_NATUREZA` em `gold.dim_evento`.

**Resultado:** 103 itens de natureza SERVICO (grupos A, B, C, D, E, H, I) e 20
de natureza AGRAVO (grupos F e G), totalizando os 123 itens da dimensão.

---

## QD-21 — Ausência de quantidade em rubrica financeira

**Sintoma:** o item H retorna nulo em toda agregação de volume.

**Investigação:** consulta de eventos por item de nível 1.

**Resultado:** o item H (Demais Despesas Médico-Hospitalares) possui despesa
registrada — R$ 81,66 bilhões no acumulado da série — mas não possui
`QT_EVENTOS`. Trata-se de rubrica contábil agregada, sem contagem de
procedimentos associada.

**Tratamento:** análises de volume excluem o item H; análises de despesa o
mantêm.

---

## QD-22 — Valores a preços correntes

**Sintoma:** a série acumula seis anos de despesa sem correção monetária.

**Resultado:** os valores de `VL_DESPESA_ASST_LIQ` somam competências de 2020 a
2025 a preços correntes.

**Tratamento:** comparações entre categorias de serviço são mantidas, pois a
distorção incide uniformemente sobre todas. Análises de evolução temporal de
valores declaram a limitação.

**Impacto:** conclusões sobre crescimento de despesa ao longo da série
incorporam inflação e não devem ser lidas como crescimento real.

---

## QD-23 — Repetição do denominador de exposição

**Sintoma:** frequência de utilização com ordem de grandeza inferior à
esperada.

**Investigação:** análise do comportamento de `QT_BENEF_FORA_CARENCIA` entre
itens de uma mesma combinação de perfil e competência.

**Causa:** a coluna representa a exposição do grupo de beneficiários, não a
exposição a cada serviço isoladamente. Somá-la ao longo de múltiplos itens e
competências multiplica o denominador.

**Tratamento:** a métrica de frequência é calculada com recorte temporal
definido — anual ou por competência — e por item assistencial. O valor
resultante permite comparação entre serviços e entre períodos, mas não
corresponde a uma taxa anual literal quando múltiplas competências são
agregadas.

**Impacto:** a limitação é declarada junto a toda leitura de frequência.

---

## QD-24 — Assimetria na cobertura de exames monitorados

**Sintoma:** volumes muito distintos entre as categorias de exame.

**Investigação:** contagem de procedimentos classificados por natureza
diagnóstica.

**Resultado:** a classificação abrange número desigual de procedimentos — 12 em
imagem, 3 em laboratorial, 3 em endoscópico e 2 em funcional.

**Causa:** o SIP monitora um subconjunto selecionado de exames, com maior
cobertura de procedimentos de imagem.

**Tratamento:** comparações restringem-se à evolução temporal dentro de cada
categoria. O volume absoluto entre categorias não é interpretado como
distribuição real do mercado.

---

## Síntese

Dos 24 achados registrados, dezesseis correspondem a problemas efetivamente
detectados e tratados; os demais são verificações preventivas cujo resultado
limpo constitui, ele próprio, evidência de conformidade.

Três achados alteraram o desenho do modelo dimensional:

| Achado | Efeito sobre a modelagem |
|---|---|
| QD-03 — hierarquia embutida no identificador | Criação da coluna `NIVEL` e filtro obrigatório em toda agregação |
| QD-04 — duas granularidades de medida | Separação em `fato_custo` e `fato_utilizacao` |
| QD-19 — naturezas distintas na mesma coluna | Criação do atributo `TP_NATUREZA` |

Um padrão se repetiu ao longo da investigação: três sintomas que aparentavam
falha de dado — ausência de despesa no nível agregado, ausência de quantidade
no item H e grupos sem registro de nível 1 — revelaram-se, após decomposição,
características da fonte. Tratá-los como sujeira e aplicar limpeza teria
descartado informação legítima.

## Verificações não realizadas

Registradas para transparência metodológica. Nenhuma é pré-requisito das
respostas obtidas.

| # | Verificação | Motivo |
|---|---|---|
| V-04 | Consistência entre a soma dos níveis 2 e o total do nível 1 | Exigiria reconciliação item a item; a fonte não garante que o agregado seja a soma exata dos componentes |
| V-06 | Faixa de valores de despesa e quantidade | Detecção de outliers não foi conduzida sistematicamente |
| V-07 | Comportamento dos agravos ao longo da série | Os grupos F e G foram mapeados, mas não analisados |

*As verificações V-01, V-02, V-03 e V-05 foram concluídas ou perderam objeto —
ver QD-08, QD-11 e QD-16. A V-02 deixou de se aplicar com a decisão de manter a
base de beneficiários fora do escopo.*
