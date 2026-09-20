# Databricks notebook source
# MAGIC %md
# MAGIC # MVP — Engenharia de Dados
# MAGIC ## Pipeline de utilização e custo assistencial na saúde suplementar brasileira
# MAGIC
# MAGIC | | |
# MAGIC |---|---|
# MAGIC | **Autor** | Isaías Cordeiro |
# MAGIC | **Curso** | PUC-Rio · Sprint de Engenharia de Dados |
# MAGIC | **Fonte** | ANS — Sistema de Informações de Produtos (SIP) |
# MAGIC | **Cobertura** | 24 competências trimestrais, de 2020-01 a 2025-10 |
# MAGIC | **Arquitetura** | Medalhão — bronze, silver e gold |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup
# MAGIC Parâmetros de conexão e padrão de leitura da fonte.

# COMMAND ----------

# Fonte: ANS, Portal de Dados Abertos (licença aberta, Dec. 8.777/2016)

import pandas as pd

BASE = "https://dadosabertos.ans.gov.br/FTP/PDA/"

# Padrão de leitura definido após inspeção da fonte:
#   sep=";"          separador brasileiro
#   encoding="utf-8" o SIP é UTF-8 (o cadastro de operadoras é latin-1)
#   dtype=str        sem conversão na bronze; preserva zeros à esquerda
LEITURA = dict(sep=";", encoding="utf-8", dtype=str)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Camadas
# MAGIC Criação dos três schemas da arquitetura medalhão, com descrição gravada no Unity Catalog.

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC CREATE SCHEMA IF NOT EXISTS bronze
# MAGIC   COMMENT 'Camada bruta. Dados como recebidos da ANS, sem transformação.';
# MAGIC
# MAGIC CREATE SCHEMA IF NOT EXISTS silver
# MAGIC   COMMENT 'Camada limpa. Tipagem, deduplicação e enriquecimento.';
# MAGIC
# MAGIC CREATE SCHEMA IF NOT EXISTS gold
# MAGIC   COMMENT 'Camada analítica. Esquema estrela: fatos e dimensões.';

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Bronze — ingestão
# MAGIC Coleta das 24 competências trimestrais direto do servidor da ANS, empilhadas em tabela única.
# MAGIC
# MAGIC Nenhuma transformação é aplicada: a estrutura original de 11 colunas é preservada e o dado permanece como texto. Acrescentam-se apenas `_arquivo_origem`, que preserva a procedência de cada registro, e `_data_ingestao`, que permite auditoria temporal.
# MAGIC
# MAGIC A escrita usa `mode("overwrite")` para garantir idempotência.

# COMMAND ----------


COMPETENCIAS = [f"{ano}{tri}" for ano in range(2020, 2026)
                              for tri in ["01","04","07","10"]]

partes = []
for comp in COMPETENCIAS:
    arq = f"sip_mapa_assistencial_{comp}.csv"
    d = pd.read_csv(BASE + "SIP/" + arq, **LEITURA)
    d["_arquivo_origem"] = arq
    d["_data_ingestao"]  = pd.Timestamp.now()
    partes.append(d)
    print(f"{comp}: {len(d):,}")

pdf = pd.concat(partes, ignore_index=True)

(spark.createDataFrame(pdf)
      .write.format("delta").mode("overwrite")
      .saveAsTable("bronze.sip"))

print(f"\nTotal: {len(pdf):,} linhas em bronze.sip")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Bronze — validação
# MAGIC Conferência de volume por arquivo, unicidade do grão e inspeção dos formatos numéricos da fonte.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT _arquivo_origem, COUNT(*) AS linhas
# MAGIC FROM bronze.sip
# MAGIC GROUP BY _arquivo_origem
# MAGIC ORDER BY _arquivo_origem;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(*) AS total,
# MAGIC        COUNT(DISTINCT PORTE_OPERADORA, GR_MODALIDADE, COBERTURA,
# MAGIC                       CONTRATACAO, ID_TRIMESTRE, ID_ITEM_ASST) AS combinacoes_unicas
# MAGIC FROM bronze.sip;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT VL_DESPESA_ASST_LIQ, QT_EVENTOS
# MAGIC FROM bronze.sip
# MAGIC WHERE VL_DESPESA_ASST_LIQ IS NOT NULL
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Silver — transformação
# MAGIC Tipagem e enriquecimento. A conversão numérica trata separadamente as duas convenções decimais presentes na fonte: vírgula na despesa e ponto na quantidade.
# MAGIC
# MAGIC Três atributos são derivados: `NIVEL`, pela contagem de separadores do código hierárquico; `LG_ITEM_SEM_DESPESA`, que sinaliza os itens E1 e E2; e a dimensão `dim_classif_exame`, que classifica os exames por natureza diagnóstica.

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC CREATE OR REPLACE TABLE silver.sip AS
# MAGIC SELECT
# MAGIC   PORTE_OPERADORA,
# MAGIC   GR_MODALIDADE,
# MAGIC   COBERTURA,
# MAGIC   CONTRATACAO,
# MAGIC   ID_TRIMESTRE,
# MAGIC   ID_ITEM_ASST,
# MAGIC   DE_ITEM_ASST,
# MAGIC
# MAGIC   size(split(ID_ITEM_ASST, '\\.')) AS NIVEL,
# MAGIC
# MAGIC   CASE WHEN ID_ITEM_ASST IN ('E1','E2') THEN true ELSE false END
# MAGIC     AS LG_ITEM_SEM_DESPESA,
# MAGIC
# MAGIC   CAST(QT_EVENTOS AS DECIMAL(18,0))              AS QT_EVENTOS,
# MAGIC   CAST(QT_BENEF_FORA_CARENCIA AS DECIMAL(18,0))  AS QT_BENEF_FORA_CARENCIA,
# MAGIC   CAST(replace(VL_DESPESA_ASST_LIQ, ',', '.') AS DECIMAL(18,2))
# MAGIC                                                  AS VL_DESPESA_ASST_LIQ,
# MAGIC
# MAGIC   CAST(DT_CORTE AS DATE)          AS DT_CORTE,
# MAGIC   _arquivo_origem,
# MAGIC   _data_ingestao
# MAGIC FROM bronze.sip;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Silver — validação
# MAGIC Comparação da contagem de nulos entre as camadas, confirmando que a conversão de tipos não introduziu perdas.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'bronze' AS camada,
# MAGIC        SUM(CASE WHEN QT_EVENTOS IS NULL THEN 1 ELSE 0 END) AS nulos_eventos,
# MAGIC        SUM(CASE WHEN VL_DESPESA_ASST_LIQ IS NULL THEN 1 ELSE 0 END) AS nulos_despesa
# MAGIC FROM bronze.sip
# MAGIC UNION ALL
# MAGIC SELECT 'silver',
# MAGIC        SUM(CASE WHEN QT_EVENTOS IS NULL THEN 1 ELSE 0 END),
# MAGIC        SUM(CASE WHEN VL_DESPESA_ASST_LIQ IS NULL THEN 1 ELSE 0 END)
# MAGIC FROM silver.sip;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT DISTINCT ID_ITEM_ASST, DE_ITEM_ASST
# MAGIC FROM silver.sip
# MAGIC WHERE ID_ITEM_ASST LIKE 'C.%' AND NIVEL = 2
# MAGIC ORDER BY ID_ITEM_ASST;

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC --CLASSIFICAÇÃO DOS EXAMES
# MAGIC
# MAGIC -- SILVER — dimensão derivada: classificação de exames (DT-13)
# MAGIC --
# MAGIC -- A ANS não classifica exames por natureza diagnóstica: o nível 2
# MAGIC -- do item C desce direto ao procedimento. A atribuição abaixo é
# MAGIC -- autoral, com critério baseado na descrição do procedimento.
# MAGIC --
# MAGIC -- Categorias ENDOSCOPICO e FUNCIONAL foram criadas para evitar
# MAGIC -- enquadramento forçado de procedimentos que não são nem imagem
# MAGIC -- nem laboratório.
# MAGIC
# MAGIC
# MAGIC CREATE OR REPLACE TABLE silver.dim_classif_exame AS
# MAGIC SELECT * FROM VALUES
# MAGIC   ('C.01','IMAGEM'),        -- Ressonância magnética
# MAGIC   ('C.02','IMAGEM'),        -- Tomografia computadorizada
# MAGIC   ('C.04','IMAGEM'),        -- Densitometria óssea
# MAGIC   ('C.05','IMAGEM'),        -- Ecodopplercardiograma
# MAGIC   ('C.10','IMAGEM'),        -- Mamografia
# MAGIC   ('C.11','IMAGEM'),        -- Cintilografia miocárdica
# MAGIC   ('C.12','IMAGEM'),        -- Cintilografia renal
# MAGIC   ('C.15','IMAGEM'),        -- Radiografia
# MAGIC   ('C.17','IMAGEM'),        -- USG abdome total
# MAGIC   ('C.18','IMAGEM'),        -- USG abdome inferior
# MAGIC   ('C.19','IMAGEM'),        -- USG abdome superior
# MAGIC   ('C.20','IMAGEM'),        -- USG obstétrica morfológica
# MAGIC   ('C.03','LABORATORIAL'),  -- Citopatologia cérvico-vaginal
# MAGIC   ('C.13','LABORATORIAL'),  -- Hemoglobina glicada
# MAGIC   ('C.14','LABORATORIAL'),  -- Sangue oculto nas fezes
# MAGIC   ('C.06','ENDOSCOPICO'),   -- Broncoscopia
# MAGIC   ('C.07','ENDOSCOPICO'),   -- Endoscopia digestiva alta
# MAGIC   ('C.08','ENDOSCOPICO'),   -- Colonoscopia
# MAGIC   ('C.09','FUNCIONAL'),     -- Holter 24h
# MAGIC   ('C.16','FUNCIONAL')      -- Teste ergométrico
# MAGIC AS t(ID_ITEM_ASST, CLASSIF_EXAME);

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT s.ID_ITEM_ASST, s.DE_ITEM_ASST
# MAGIC FROM (SELECT DISTINCT ID_ITEM_ASST, DE_ITEM_ASST FROM silver.sip
# MAGIC       WHERE ID_ITEM_ASST LIKE 'C.%' AND NIVEL = 2) s
# MAGIC LEFT JOIN silver.dim_classif_exame d USING (ID_ITEM_ASST)
# MAGIC WHERE d.CLASSIF_EXAME IS NULL;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Gold — modelo dimensional
# MAGIC Esquema estrela com três dimensões conformadas e duas tabelas fato.
# MAGIC
# MAGIC A separação em dois fatos decorre da estrutura da fonte: despesa e beneficiários expostos são reportados apenas no nível 1 da hierarquia, enquanto a quantidade de eventos é reportada em todos os níveis. Modelar em tabela única exigiria descartar 80% das linhas ou conviver com medidas majoritariamente nulas.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold.dim_tempo AS
# MAGIC SELECT DISTINCT
# MAGIC   ID_TRIMESTRE                               AS SK_TEMPO,
# MAGIC   CAST(substring(ID_TRIMESTRE, 1, 4) AS INT) AS NR_ANO,
# MAGIC   CAST(substring(ID_TRIMESTRE, 6, 2) AS INT) AS NR_MES_COMPETENCIA,
# MAGIC   CASE substring(ID_TRIMESTRE, 6, 2)
# MAGIC     WHEN '01' THEN 1 WHEN '04' THEN 2
# MAGIC     WHEN '07' THEN 3 WHEN '10' THEN 4 END    AS NR_TRIMESTRE
# MAGIC FROM silver.sip;
# MAGIC
# MAGIC CREATE OR REPLACE TABLE gold.dim_evento AS
# MAGIC SELECT DISTINCT
# MAGIC   s.ID_ITEM_ASST                  AS SK_EVENTO,
# MAGIC   s.DE_ITEM_ASST                  AS DS_EVENTO,
# MAGIC   s.NIVEL,
# MAGIC   substring(s.ID_ITEM_ASST, 1, 1) AS CD_GRUPO,
# MAGIC   CASE WHEN substring(s.ID_ITEM_ASST,1,1) IN ('F','G')
# MAGIC        THEN 'AGRAVO' ELSE 'SERVICO' END AS TP_NATUREZA,
# MAGIC   s.LG_ITEM_SEM_DESPESA,
# MAGIC   c.CLASSIF_EXAME
# MAGIC FROM silver.sip s
# MAGIC LEFT JOIN silver.dim_classif_exame c USING (ID_ITEM_ASST);
# MAGIC
# MAGIC CREATE OR REPLACE TABLE gold.dim_perfil_operadora AS
# MAGIC SELECT DISTINCT
# MAGIC   concat_ws('|', PORTE_OPERADORA, GR_MODALIDADE, COBERTURA, CONTRATACAO) AS SK_PERFIL,
# MAGIC   PORTE_OPERADORA,
# MAGIC   GR_MODALIDADE,
# MAGIC   COBERTURA,
# MAGIC   CONTRATACAO
# MAGIC FROM silver.sip;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'dim_tempo' AS dim, COUNT(*) AS linhas, COUNT(DISTINCT SK_TEMPO) AS chaves FROM gold.dim_tempo
# MAGIC UNION ALL SELECT 'dim_evento', COUNT(*), COUNT(DISTINCT SK_EVENTO) FROM gold.dim_evento
# MAGIC UNION ALL SELECT 'dim_perfil', COUNT(*), COUNT(DISTINCT SK_PERFIL) FROM gold.dim_perfil_operadora;

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC -- GOLD — fato de custo
# MAGIC
# MAGIC -- Grão: nível 1 da hierarquia, excluídos E1 e E2 (QD-05)
# MAGIC -- Medidas: despesa, beneficiários expostos e eventos agregados
# MAGIC
# MAGIC
# MAGIC CREATE OR REPLACE TABLE gold.fato_custo AS
# MAGIC SELECT
# MAGIC   ID_TRIMESTRE                                                          AS SK_TEMPO,
# MAGIC   ID_ITEM_ASST                                                          AS SK_EVENTO,
# MAGIC   concat_ws('|', PORTE_OPERADORA, GR_MODALIDADE, COBERTURA, CONTRATACAO) AS SK_PERFIL,
# MAGIC   QT_EVENTOS,
# MAGIC   QT_BENEF_FORA_CARENCIA,
# MAGIC   VL_DESPESA_ASST_LIQ
# MAGIC FROM silver.sip
# MAGIC WHERE NIVEL = 1
# MAGIC   AND LG_ITEM_SEM_DESPESA = false;

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC -- GOLD — fato de utilização
# MAGIC
# MAGIC -- Grão: níveis 2, 3 e 4 — detalhe por procedimento
# MAGIC -- Medida única: quantidade de eventos (QD-04)
# MAGIC
# MAGIC
# MAGIC CREATE OR REPLACE TABLE gold.fato_utilizacao AS
# MAGIC SELECT
# MAGIC   ID_TRIMESTRE                                                          AS SK_TEMPO,
# MAGIC   ID_ITEM_ASST                                                          AS SK_EVENTO,
# MAGIC   concat_ws('|', PORTE_OPERADORA, GR_MODALIDADE, COBERTURA, CONTRATACAO) AS SK_PERFIL,
# MAGIC   QT_EVENTOS
# MAGIC FROM silver.sip
# MAGIC WHERE NIVEL IN (2, 3, 4);

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Gold — catálogo de dados
# MAGIC Documentação das cinco tabelas e de suas colunas no Unity Catalog, incluindo domínio de valores, linhagem e aditividade das medidas.

# COMMAND ----------

# MAGIC %sql
# MAGIC COMMENT ON TABLE gold.fato_custo IS
# MAGIC   'Fato de custo assistencial. Grão: item de nível 1 x trimestre x perfil de operadora. Exclui E1 e E2, que não possuem despesa por definição.';
# MAGIC
# MAGIC COMMENT ON TABLE gold.fato_utilizacao IS
# MAGIC   'Fato de utilização detalhada. Grão: itens de níveis 2 a 4 x trimestre x perfil. Medida única: quantidade de eventos.';
# MAGIC
# MAGIC COMMENT ON TABLE gold.dim_tempo IS
# MAGIC   'Dimensão temporal. Grão: uma linha por competência trimestral, de 2020-01 a 2025-10.';
# MAGIC
# MAGIC COMMENT ON TABLE gold.dim_evento IS
# MAGIC   'Dimensão de item assistencial, com atributos derivados de nível, grupo, natureza e classificação de exame.';
# MAGIC
# MAGIC COMMENT ON TABLE gold.dim_perfil_operadora IS
# MAGIC   'Dimensão de perfil. Grão: combinação de porte, modalidade, cobertura e tipo de contratação.';

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE gold.dim_evento ALTER COLUMN SK_EVENTO
# MAGIC   COMMENT 'Chave do item assistencial. Código hierárquico da ANS, com níveis separados por ponto.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_evento ALTER COLUMN DS_EVENTO
# MAGIC   COMMENT 'Descrição do item assistencial conforme publicada pela ANS.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_evento ALTER COLUMN NIVEL
# MAGIC   COMMENT 'Profundidade hierárquica do item, obtida pela contagem de separadores. Domínio: 1 a 4.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_evento ALTER COLUMN CD_GRUPO
# MAGIC   COMMENT 'Grupo assistencial, obtido pelo primeiro caractere do código. Domínio: A a I.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_evento ALTER COLUMN TP_NATUREZA
# MAGIC   COMMENT 'Natureza do item. SERVICO (103 itens) ou AGRAVO (20 itens, grupos F e G). Agregações devem filtrar por esta coluna.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_evento ALTER COLUMN LG_ITEM_SEM_DESPESA
# MAGIC   COMMENT 'Indica item sem despesa própria por definição. Verdadeiro para E1 e E2, desdobramentos qualitativos de internação.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_evento ALTER COLUMN CLASSIF_EXAME
# MAGIC   COMMENT 'Natureza diagnóstica do exame. Dimensão derivada autoral, não consta da fonte. IMAGEM, LABORATORIAL, ENDOSCOPICO, FUNCIONAL.';

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE EXTENDED gold.dim_evento;

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE gold.dim_tempo ALTER COLUMN SK_TEMPO
# MAGIC   COMMENT 'Chave da competência trimestral no formato AAAA-MM. Domínio: 2020-01 a 2025-10.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_tempo ALTER COLUMN NR_ANO
# MAGIC   COMMENT 'Ano da competência. Domínio: 2020 a 2025.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_tempo ALTER COLUMN NR_MES_COMPETENCIA
# MAGIC   COMMENT 'Mês de referência da competência. Domínio: 1, 4, 7, 10.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_tempo ALTER COLUMN NR_TRIMESTRE
# MAGIC   COMMENT 'Trimestre do ano, derivado do mês de competência. Domínio: 1 a 4.';

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE gold.dim_tempo;

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE gold.dim_perfil_operadora ALTER COLUMN SK_PERFIL
# MAGIC   COMMENT 'Chave composta pela concatenação de porte, modalidade, cobertura e contratação. 82 combinações observadas.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_perfil_operadora ALTER COLUMN PORTE_OPERADORA
# MAGIC   COMMENT 'Porte da operadora. Domínio: PEQUENO, MEDIO, GRANDE.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_perfil_operadora ALTER COLUMN GR_MODALIDADE
# MAGIC   COMMENT 'Modalidade da operadora. Sete valores, entre eles Autogestão, Cooperativa Médica, Medicina de Grupo, Odontologia de Grupo e Seguradora.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_perfil_operadora ALTER COLUMN COBERTURA
# MAGIC   COMMENT 'Tipo de cobertura. Domínio: MÉDICO-HOSPITALAR, ODONTOLÓGICO.';
# MAGIC
# MAGIC ALTER TABLE gold.dim_perfil_operadora ALTER COLUMN CONTRATACAO
# MAGIC   COMMENT 'Canal de contratação. Domínio: Individual ou familiar, Coletivo Empresarial, Coletivo por Adesão.';

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE gold.dim_perfil_operadora;

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE gold.fato_custo ALTER COLUMN SK_TEMPO
# MAGIC   COMMENT 'Chave estrangeira para gold.dim_tempo.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_custo ALTER COLUMN SK_EVENTO
# MAGIC   COMMENT 'Chave estrangeira para gold.dim_evento. Restrita ao nível 1, exceto E1 e E2.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_custo ALTER COLUMN SK_PERFIL
# MAGIC   COMMENT 'Chave estrangeira para gold.dim_perfil_operadora.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_custo ALTER COLUMN QT_EVENTOS
# MAGIC   COMMENT 'Quantidade de eventos realizados no período. Medida aditiva. Nula para o item H, rubrica sem contagem de procedimentos.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_custo ALTER COLUMN QT_BENEF_FORA_CARENCIA
# MAGIC   COMMENT 'Beneficiários aptos a utilizar o serviço. Semiaditiva: repete-se entre itens do mesmo perfil e competência. Denominador da frequência de utilização.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_custo ALTER COLUMN VL_DESPESA_ASST_LIQ
# MAGIC   COMMENT 'Despesa assistencial líquida em reais, a preços correntes, sem deflação. Medida aditiva.';

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE gold.fato_custo;

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE gold.fato_utilizacao ALTER COLUMN SK_TEMPO
# MAGIC   COMMENT 'Chave estrangeira para gold.dim_tempo.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_utilizacao ALTER COLUMN SK_EVENTO
# MAGIC   COMMENT 'Chave estrangeira para gold.dim_evento. Restrita aos níveis 2, 3 e 4.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_utilizacao ALTER COLUMN SK_PERFIL
# MAGIC   COMMENT 'Chave estrangeira para gold.dim_perfil_operadora.';
# MAGIC
# MAGIC ALTER TABLE gold.fato_utilizacao ALTER COLUMN QT_EVENTOS
# MAGIC   COMMENT 'Quantidade de eventos realizados no período. Medida aditiva. Única medida deste fato.';

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE gold.fato_utilizacao;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT table_name, comment
# MAGIC FROM system.information_schema.tables
# MAGIC WHERE table_schema = 'gold'
# MAGIC ORDER BY table_name;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Gold — validação
# MAGIC Unicidade das chaves dimensionais, integridade referencial entre fatos e dimensões, e rastreabilidade da carga entre as camadas.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'fato_custo' AS fato, COUNT(*) AS linhas,
# MAGIC        SUM(CASE WHEN t.SK_TEMPO IS NULL THEN 1 ELSE 0 END) AS orfaos_tempo,
# MAGIC        SUM(CASE WHEN e.SK_EVENTO IS NULL THEN 1 ELSE 0 END) AS orfaos_evento,
# MAGIC        SUM(CASE WHEN p.SK_PERFIL IS NULL THEN 1 ELSE 0 END) AS orfaos_perfil
# MAGIC FROM gold.fato_custo f
# MAGIC LEFT JOIN gold.dim_tempo t USING (SK_TEMPO)
# MAGIC LEFT JOIN gold.dim_evento e USING (SK_EVENTO)
# MAGIC LEFT JOIN gold.dim_perfil_operadora p USING (SK_PERFIL)
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 'fato_utilizacao', COUNT(*),
# MAGIC        SUM(CASE WHEN t.SK_TEMPO IS NULL THEN 1 ELSE 0 END),
# MAGIC        SUM(CASE WHEN e.SK_EVENTO IS NULL THEN 1 ELSE 0 END),
# MAGIC        SUM(CASE WHEN p.SK_PERFIL IS NULL THEN 1 ELSE 0 END)
# MAGIC FROM gold.fato_utilizacao f
# MAGIC LEFT JOIN gold.dim_tempo t USING (SK_TEMPO)
# MAGIC LEFT JOIN gold.dim_evento e USING (SK_EVENTO)
# MAGIC LEFT JOIN gold.dim_perfil_operadora p USING (SK_PERFIL);

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT NIVEL,
# MAGIC        LG_ITEM_SEM_DESPESA,
# MAGIC        COUNT(*) AS linhas
# MAGIC FROM silver.sip
# MAGIC GROUP BY NIVEL, LG_ITEM_SEM_DESPESA
# MAGIC ORDER BY NIVEL;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT DISTINCT ID_ITEM_ASST, DE_ITEM_ASST
# MAGIC FROM silver.sip
# MAGIC WHERE NIVEL = 4
# MAGIC ORDER BY ID_ITEM_ASST;
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Qualidade de dados
# MAGIC Investigação da estrutura hierárquica do identificador, da distribuição de nulos entre níveis e da natureza dos grupos F e G.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT DISTINCT substring(ID_ITEM_ASST,1,1) AS grupo, NIVEL, COUNT(*) AS linhas
# MAGIC FROM silver.sip
# MAGIC GROUP BY 1, 2
# MAGIC ORDER BY 1, 2;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT DISTINCT substring(ID_ITEM_ASST,1,4) AS item, DE_ITEM_ASST
# MAGIC FROM silver.sip
# MAGIC WHERE ID_ITEM_ASST LIKE 'F%' OR ID_ITEM_ASST LIKE 'G%'
# MAGIC ORDER BY 1;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT TP_NATUREZA, COUNT(*) AS itens
# MAGIC FROM gold.dim_evento
# MAGIC GROUP BY TP_NATUREZA;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Análises
# MAGIC Respostas às perguntas de negócio formuladas na etapa de objetivo.

# COMMAND ----------

# MAGIC %md
# MAGIC ###  Quais tipos de evento concentram o maior volume de utilização?
# MAGIC Agregação por item assistencial de nível 1, restrita à natureza SERVIÇO.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT e.DS_EVENTO,
# MAGIC        SUM(f.QT_EVENTOS) AS total_eventos
# MAGIC FROM gold.fato_custo f
# MAGIC JOIN gold.dim_evento e ON f.SK_EVENTO = e.SK_EVENTO
# MAGIC WHERE e.TP_NATUREZA = 'SERVICO'
# MAGIC GROUP BY e.DS_EVENTO
# MAGIC ORDER BY total_eventos DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Qual o custo médio por evento?
# MAGIC Volume e despesa lado a lado, para contrastar frequência de uso e impacto financeiro.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT e.DS_EVENTO,
# MAGIC        SUM(f.QT_EVENTOS) AS eventos,
# MAGIC        ROUND(SUM(f.VL_DESPESA_ASST_LIQ)/1e9, 2) AS despesa_bi,
# MAGIC        ROUND(SUM(f.VL_DESPESA_ASST_LIQ)/NULLIF(SUM(f.QT_EVENTOS),0), 2) AS custo_medio_evento
# MAGIC FROM gold.fato_custo f
# MAGIC JOIN gold.dim_evento e ON f.SK_EVENTO = e.SK_EVENTO
# MAGIC WHERE e.TP_NATUREZA = 'SERVICO'
# MAGIC GROUP BY e.DS_EVENTO
# MAGIC ORDER BY despesa_bi DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ###  Qual a frequência de utilização por beneficiário exposto?
# MAGIC O denominador utiliza beneficiários fora do período de carência, e não a carteira total, evitando subestimar a frequência ao incluir quem está impedido de utilizar o serviço.
# MAGIC
# MAGIC A medida é não aditiva: numerador e denominador são somados antes da divisão.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT e.DS_EVENTO,
# MAGIC        SUM(f.QT_EVENTOS) AS eventos,
# MAGIC        SUM(f.QT_BENEF_FORA_CARENCIA) AS benef_expostos,
# MAGIC        ROUND(SUM(f.QT_EVENTOS)/NULLIF(SUM(f.QT_BENEF_FORA_CARENCIA),0), 2) AS eventos_por_benef
# MAGIC FROM gold.fato_custo f
# MAGIC JOIN gold.dim_evento e ON f.SK_EVENTO = e.SK_EVENTO
# MAGIC WHERE e.TP_NATUREZA = 'SERVICO'
# MAGIC GROUP BY e.DS_EVENTO
# MAGIC ORDER BY eventos_por_benef DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Como a utilização evoluiu ao longo da série?
# MAGIC Agregação anual, que neutraliza a variação sazonal intra-ano.
# MAGIC
# MAGIC O ano de 2020 é atípico pelo adiamento de procedimentos eletivos durante a pandemia. A variação entre 2020 e 2021 deve ser lida como recuperação de demanda represada, não como tendência.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT t.NR_ANO,
# MAGIC        e.DS_EVENTO,
# MAGIC        SUM(f.QT_EVENTOS) AS eventos,
# MAGIC        ROUND(SUM(f.QT_EVENTOS)/NULLIF(SUM(f.QT_BENEF_FORA_CARENCIA),0), 3) AS freq_ano
# MAGIC FROM gold.fato_custo f
# MAGIC JOIN gold.dim_evento e ON f.SK_EVENTO = e.SK_EVENTO
# MAGIC JOIN gold.dim_tempo  t ON f.SK_TEMPO  = t.SK_TEMPO
# MAGIC WHERE e.TP_NATUREZA = 'SERVICO'
# MAGIC GROUP BY t.NR_ANO, e.DS_EVENTO
# MAGIC ORDER BY e.DS_EVENTO, t.NR_ANO;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Desdobramento — Onde se originou a retração odontológica?
# MAGIC A série anual mostrou queda na utilização odontológica a partir de 2022, isolada entre os serviços. Esta análise decompõe o movimento por canal de contratação.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT t.NR_ANO,
# MAGIC        p.CONTRATACAO,
# MAGIC        ROUND(SUM(f.QT_EVENTOS)/NULLIF(SUM(f.QT_BENEF_FORA_CARENCIA),0), 3) AS freq
# MAGIC FROM gold.fato_custo f
# MAGIC JOIN gold.dim_evento e ON f.SK_EVENTO = e.SK_EVENTO
# MAGIC JOIN gold.dim_tempo  t ON f.SK_TEMPO  = t.SK_TEMPO
# MAGIC JOIN gold.dim_perfil_operadora p ON f.SK_PERFIL = p.SK_PERFIL
# MAGIC WHERE e.DS_EVENTO = 'PROCEDIMENTOS ODONTOLÓGICOS'
# MAGIC GROUP BY t.NR_ANO, p.CONTRATACAO
# MAGIC ORDER BY p.CONTRATACAO, t.NR_ANO;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Exames de imagem e laboratoriais têm padrões distintos?
# MAGIC Utiliza a dimensão derivada `CLASSIF_EXAME`, aplicada ao nível 2 do item C.
# MAGIC
# MAGIC A classificação abrange número desigual de procedimentos por categoria — 12 em imagem, 3 em laboratorial, 3 em endoscópico e 2 em funcional. A comparação válida é a evolução dentro de cada categoria, não o volume absoluto entre elas.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT t.NR_ANO,
# MAGIC        e.CLASSIF_EXAME,
# MAGIC        SUM(f.QT_EVENTOS) AS eventos
# MAGIC FROM gold.fato_utilizacao f
# MAGIC JOIN gold.dim_evento e ON f.SK_EVENTO = e.SK_EVENTO
# MAGIC JOIN gold.dim_tempo  t ON f.SK_TEMPO  = t.SK_TEMPO
# MAGIC WHERE e.CLASSIF_EXAME IS NOT NULL
# MAGIC   AND e.NIVEL = 2
# MAGIC GROUP BY t.NR_ANO, e.CLASSIF_EXAME
# MAGIC ORDER BY e.CLASSIF_EXAME, t.NR_ANO;