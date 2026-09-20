# Databricks notebook source
import requests, re

BASE = "https://dadosabertos.ans.gov.br/FTP/PDA/"
html = requests.get(BASE).text

pastas = re.findall(r'href="([^"]+/)"', html)
for p in pastas:
    print(p)

# COMMAND ----------

df = pd.read_csv(BASE + "SIP/sip_mapa_assistencial_202410.csv",
                 sep=";", encoding="utf-8", dtype=str)

# COMMAND ----------

def listar(pasta=""):
    html = requests.get(BASE + pasta).text
    for item in re.findall(r'href="([^"]+)"', html):
        if not item.startswith(("?", "/")):
            print(item)

listar("SIP/")

# COMMAND ----------

import pandas as pd

url = BASE + "SIP/sip_mapa_assistencial_202410.csv"

amostra = pd.read_csv(url, sep=";", encoding="latin-1", dtype=str, nrows=100)

print("Colunas:", list(amostra.columns))
display(amostra.head(10))

# COMMAND ----------

df = pd.read_csv(BASE + "SIP/sip_mapa_assistencial_202410.csv",
                 sep=";", encoding="latin-1", dtype=str)

g = ["PORTE_OPERADORA","GR_MODALIDADE","COBERTURA","CONTRATACAO","ID_TRIMESTRE"]
print(df.groupby(g)["QT_BENEF_FORA_CARENCIA"].nunique().value_counts())

# COMMAND ----------

display(df.groupby(["ID_ITEM_ASST","DE_ITEM_ASST"]).size()
          .reset_index(name="qtd_linhas"))

# COMMAND ----------

g = ["PORTE_OPERADORA","GR_MODALIDADE","COBERTURA","CONTRATACAO","ID_TRIMESTRE"]

exemplo = df.groupby(g).filter(lambda x: len(x) > 5).head(30)
display(exemplo[g + ["DE_ITEM_ASST","QT_EVENTOS","QT_BENEF_FORA_CARENCIA"]])

# COMMAND ----------

# Qualidade: nulos e volume
print("Linhas:", len(df))
print("\nNulos por coluna:")
print(df.isna().sum().to_string())

# COMMAND ----------

df["NIVEL"] = df["ID_ITEM_ASST"].str.count(r"\.") + 1

print(df.groupby("NIVEL")["ID_ITEM_ASST"].nunique())
display(df[df["NIVEL"] == 1][["ID_ITEM_ASST","DE_ITEM_ASST"]].drop_duplicates())

# COMMAND ----------

df["NIVEL"] = df["ID_ITEM_ASST"].str.count(r"\.") + 1

diag = df.groupby("NIVEL").agg(
    linhas=("ID_ITEM_ASST", "size"),
    pct_sem_benef=("QT_BENEF_FORA_CARENCIA", lambda s: round(100*s.isna().mean(),1)),
    pct_sem_despesa=("VL_DESPESA_ASST_LIQ", lambda s: round(100*s.isna().mean(),1)),
    pct_sem_eventos=("QT_EVENTOS", lambda s: round(100*s.isna().mean(),1)),
)
display(diag)

# COMMAND ----------

n1 = df[df["NIVEL"] == 1]

display(n1.groupby(["COBERTURA", "GR_MODALIDADE"]).agg(
    linhas=("ID_ITEM_ASST","size"),
    pct_sem_despesa=("VL_DESPESA_ASST_LIQ", lambda s: round(100*s.isna().mean(),1))
).reset_index())

# COMMAND ----------

mh = n1[n1["COBERTURA"] == "MÉDICO-HOSPITALAR"]

display(mh.groupby(["ID_ITEM_ASST","DE_ITEM_ASST"]).agg(
    linhas=("ID_ITEM_ASST","size"),
    pct_sem_despesa=("VL_DESPESA_ASST_LIQ", lambda s: round(100*s.isna().mean(),1))
).reset_index().sort_values("pct_sem_despesa", ascending=False))

# COMMAND ----------

display(df[df["ID_ITEM_ASST"].str.startswith("C")]
        [["ID_ITEM_ASST","DE_ITEM_ASST","NIVEL"]]
        .drop_duplicates().sort_values("ID_ITEM_ASST").head(30))
        

# COMMAND ----------

display(df[(df["ID_ITEM_ASST"].str.startswith("C.")) & (df["NIVEL"]==2)]
        [["ID_ITEM_ASST","DE_ITEM_ASST"]].drop_duplicates())

# COMMAND ----------

CLASSIF_EXAME = {
    "C.01": "IMAGEM", "C.02": "IMAGEM", "C.04": "IMAGEM",
    "C.05": "IMAGEM", "C.10": "IMAGEM", "C.11": "IMAGEM", "C.12": "IMAGEM",
    "C.03": "LABORATORIAL", "C.13": "LABORATORIAL",
    "C.06": "ENDOSCOPICO", "C.07": "ENDOSCOPICO", "C.08": "ENDOSCOPICO",
    "C.09": "FUNCIONAL",
    # completar
}

# COMMAND ----------

import requests, re, pandas as pd

BASE = "https://dadosabertos.ans.gov.br/FTP/PDA/"
LEITURA = dict(sep=";", encoding="utf-8", dtype=str)

for arq in ["sip_mapa_assistencial_202001.csv",
            "sip_mapa_assistencial_202301.csv",
            "sip_mapa_assistencial_202510.csv"]:
    cols = pd.read_csv(BASE + "SIP/" + arq, **LEITURA, nrows=5).columns
    print(f"{arq}: {len(cols)} colunas")
    print("  ", list(cols))

# COMMAND ----------

def itens_n1(arq):
    d = pd.read_csv(BASE + "SIP/" + arq, **LEITURA)
    d = d[d["ID_ITEM_ASST"].str.count(r"\.") == 0]
    return set(d["ID_ITEM_ASST"].unique())

a, b = itens_n1("sip_mapa_assistencial_202001.csv"), itens_n1("sip_mapa_assistencial_202510.csv")

print("2020:", sorted(a))
print("2025:", sorted(b))
print("Só em 2020:", sorted(a - b))
print("Só em 2025:", sorted(b - a))

# COMMAND ----------

import pandas as pd

comps = [f"{a}{t}" for a in range(2020, 2026) for t in ["01","04","07","10"]]
reg = []

for c in comps:
    try:
        d = pd.read_csv(BASE + f"SIP/sip_mapa_assistencial_{c}.csv", **LEITURA)
        n1 = d[d["ID_ITEM_ASST"].str.count(r"\.") == 0]["ID_ITEM_ASST"].nunique()
        reg.append({"competencia": c, "linhas": len(d), "itens_n1": n1})
    except Exception as e:
        reg.append({"competencia": c, "linhas": None, "itens_n1": f"ERRO: {e}"})

display(pd.DataFrame(reg))

# COMMAND ----------

html = requests.get(BASE + "dados_de_beneficiarios_por_operadora/").text
for item in re.findall(r'href="([^"]+)"', html):
    if not item.startswith(("?", "/")):
        print(item)

# COMMAND ----------

url = BASE + "dados_de_beneficiarios_por_operadora/sib_ativo_MG.zip"

ben = pd.read_csv(url, compression="zip", **LEITURA, nrows=100)

print(list(ben.columns))
display(ben.head())


# COMMAND ----------

d = pd.read_csv(BASE + "dados_de_beneficiarios_por_operadora/sib_ativo_AC.zip",
                compression="zip", **LEITURA)
print("Acre:", len(d), "linhas")

# COMMAND ----------

import time

for uf in ["MG", "SP"]:
    t = time.time()
    d = pd.read_csv(BASE + f"dados_de_beneficiarios_por_operadora/sib_ativo_{uf}.zip",
                    compression="zip", **LEITURA)
    print(f"{uf}: {len(d):,} linhas | {time.time()-t:.0f}s | {d.memory_usage(deep=True).sum()/1e9:.1f} GB")
    del d

# COMMAND ----------

import pandas as pd

BASE = "https://dadosabertos.ans.gov.br/FTP/PDA/"
LEITURA = dict(sep=";", encoding="utf-8", dtype=str)

# COMMAND ----------

CHAVES = ["ID_TEMPO_COMPETENCIA","REGISTRO_OPERADORA","SG_UF",
          "TP_SEXO","LG_BENEFICIARIO_ATIVO"]

url = BASE + "dados_de_beneficiarios_por_operadora/sib_ativo_AC.zip"
partes = []

for ch in pd.read_csv(url, compression="zip", **LEITURA, chunksize=200_000):
    ch["CANCELADO"] = ch["DT_CANCELAMENTO"].notna()
    partes.append(ch.groupby(CHAVES + ["CANCELADO"], observed=True).size())

resultado = pd.concat(partes).groupby(level=list(range(6))).sum().reset_index(name="QT")
print(len(resultado), "linhas agregadas (de 67.429 originais)")
display(resultado.head())
