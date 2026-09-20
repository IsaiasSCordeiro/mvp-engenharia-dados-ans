# Resultados das Análises — registro de evidências

**MVP Engenharia de Dados | PUC-Rio | Fonte: ANS/SIP (2020–2025)**

Documento de trabalho. Alimenta a seção *Análise de Dados (Etapa 4.5)* do
README final. Cada bloco registra a pergunta, a consulta, o resultado e a
discussão.

Todas as consultas partem da camada gold. Salvo indicação contrária, os
resultados agregam as 24 competências trimestrais da série.

---

## Pergunta 3 — Quais tipos de evento concentram o maior volume de utilização?

**Consulta:** `fato_custo` filtrado por `TP_NATUREZA = 'SERVICO'`, agregado por
item assistencial de nível 1.

**Resultado — volume acumulado 2020 a 2025:**

| Posição | Evento | Eventos | Participação |
|---|---|---|---|
| 1 | Exames | 6.459.093.320 | 60% |
| 2 | Consultas médicas | 1.552.234.173 | 14% |
| 3 | Procedimentos odontológicos | 1.102.350.125 | 10% |
| 4 | Outros atendimentos ambulatoriais | 1.069.208.953 | 10% |
| 5 | Terapias | 403.430.172 | 4% |
| 6 | Internações | 52.038.843 | 0,5% |
| — | Demais despesas médico-hospitalares | sem contagem | — |

**Discussão:** exames respondem sozinhos por 60% do volume assistencial,
superando a soma de todos os demais serviços e representando mais de quatro
vezes o volume de consultas médicas. A proporção é compatível com a prática
clínica, em que uma consulta costuma originar múltiplas solicitações de exame.

Procedimentos odontológicos ocupam a terceira posição, à frente de outros
atendimentos ambulatoriais. Para um produto historicamente tratado como
complementar, o volume equivalente ao de serviços do núcleo ambulatorial indica
utilização efetiva, não apenas cobertura contratada.

Internações representam 0,5% do volume — a menor participação entre os serviços
com contagem disponível.

---

## Pergunta 7 — Custo médio por evento e distribuição da despesa

**Consulta:** `fato_custo` com despesa e volume lado a lado, por item de nível
1.

**Resultado — acumulado 2020 a 2025, preços correntes:**

| Evento | Eventos | Despesa (R$ bi) | Custo médio por evento |
|---|---|---|---|
| Internações | 52.038.843 | 610,57 | R$ 11.732,92 |
| Exames | 6.459.093.320 | 275,60 | R$ 42,67 |
| Consultas médicas | 1.552.234.173 | 182,12 | R$ 117,33 |
| Terapias | 403.430.172 | 138,54 | R$ 343,41 |
| Outros ambulatoriais | 1.069.208.953 | 131,68 | R$ 123,15 |
| Demais despesas méd.-hosp. | — | 81,66 | — |
| Procedimentos odontológicos | 1.102.350.125 | 20,95 | R$ 19,01 |

**Discussão:** a ordenação por despesa inverte integralmente a ordenação por
volume. Internações concentram 43% da despesa assistencial total com 0,5% do
volume, a um custo unitário 275 vezes superior ao de um exame. A concentração
explica por que a gestão de risco no setor se organiza em torno da prevenção de
internações.

O comportamento oposto aparece nos procedimentos odontológicos: volume
equivalente ao de outros atendimentos ambulatoriais, com despesa seis vezes
menor e o menor custo unitário da série. A combinação de alta frequência com
baixo custo unitário caracteriza um serviço de exposição financeira reduzida e
percepção de uso recorrente.

**Limitação:** valores a preços correntes, sem deflação (QD-22). A comparação
entre categorias não é afetada; leituras de evolução de valor, sim.

---

## Pergunta 4 — Frequência de utilização por beneficiário exposto

**Métrica:** eventos divididos por `QT_BENEF_FORA_CARENCIA`, somando numerador
e denominador antes da divisão (DT-20).

**Resultado — acumulado da série:**

| Evento | Frequência relativa |
|---|---|
| Exames | 5,45 |
| Procedimentos odontológicos | 1,40 |
| Consultas médicas | 1,29 |
| Outros atendimentos ambulatoriais | 0,90 |
| Terapias | 0,34 |
| Internações | 0,05 |

**Discussão:** normalizada pela exposição, a utilização odontológica supera a
de consultas médicas. O denominador utiliza beneficiários fora do período de
carência, e não a carteira total, o que evita subestimar a frequência ao
incluir beneficiários impedidos de utilizar o serviço.

**Limitação:** a agregação de 24 competências multiplica o denominador (QD-23).
Os valores permitem comparação entre serviços, mas não correspondem a uma taxa
anual literal.

---

## Perguntas 9 e 10 — Evolução da utilização ao longo da série

**Consulta:** frequência por ano e por item assistencial de nível 1.

**Resultado — eventos por beneficiário exposto:**

| Evento | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Exames | 4,181 | 5,237 | 5,652 | 5,871 | 5,796 | 5,850 |
| Procedimentos odontológicos | 1,394 | 1,484 | 1,491 | 1,429 | 1,291 | 1,361 |
| Consultas médicas | 1,080 | 1,212 | 1,334 | 1,357 | 1,373 | 1,361 |
| Outros ambulatoriais | 0,740 | 0,803 | 0,905 | 0,980 | 0,984 | 0,979 |
| Terapias | 0,300 | 0,331 | 0,347 | 0,404 | 0,336 | 0,345 |
| Internações | 0,041 | 0,042 | 0,047 | 0,048 | 0,047 | 0,050 |

**Discussão:** a série apresenta padrão comum de recuperação seguida de
estabilização. Exames crescem 25% entre 2020 e 2021 e estabilizam a partir de
2022, oscilando em torno de 5,8. Consultas e outros atendimentos ambulatoriais
seguem o mesmo comportamento, atingindo patamar em 2023 e permanecendo nele.

O ano de 2020 é atípico pelo adiamento de procedimentos eletivos durante a
pandemia (DT-22), de modo que a variação 2020–2021 representa recuperação de
demanda represada, não crescimento estrutural. A estabilização posterior indica
que a demanda represada foi absorvida.

Procedimentos odontológicos são a única exceção ao padrão: crescem até 2022
(1,491), retraem em 2023 e 2024 (1,291, queda de 13% em relação ao pico) e
recuperam parcialmente em 2025 (1,361), sem retornar ao patamar anterior.

---

## Desdobramento — Origem da retração odontológica

**Consulta:** frequência odontológica por ano e tipo de contratação.

**Resultado:**

| Tipo de contratação | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Variação pico→2024 |
|---|---|---|---|---|---|---|---|
| Individual ou familiar | 1,782 | 1,827 | 1,836 | 1,702 | 1,336 | 1,525 | −27% |
| Coletivo empresarial | 1,408 | 1,498 | 1,499 | 1,438 | 1,317 | 1,386 | −12% |
| Coletivo por adesão | 0,990 | 1,093 | 1,135 | 1,126 | 1,096 | 1,054 | −3% |

**Discussão:** a retração concentra-se na contratação individual, que perde 27%
da frequência entre o pico de 2022 e 2024, recuperando parcialmente em 2025. O
coletivo empresarial apresenta retração intermediária e o coletivo por adesão
mantém-se praticamente estável, com variação de apenas 3% em seis anos.

A hierarquia de frequência é consistente em toda a série: individual acima de
coletivo empresarial, que por sua vez está acima de coletivo por adesão. O
padrão é compatível com seleção adversa — na contratação individual a decisão
de compra é tomada pelo próprio beneficiário, que tende a contratar quando
antecipa necessidade de uso. No coletivo por adesão, a adesão ocorre no âmbito
de uma entidade de classe, de modo que parte dos beneficiários não exerce o
uso.

Para operação no coletivo por adesão, o resultado indica frequência baixa e
previsível, com variação inferior à dos demais canais ao longo de seis anos.
Combinado ao custo unitário de R$ 19,01, caracteriza exposição financeira
reduzida e previsível.

---

## Pergunta 6 — Exames de imagem e laboratoriais

**Consulta:** `fato_utilizacao` no nível 2, agregado pela dimensão derivada
`CLASSIF_EXAME` (DT-13).

**Resultado — eventos em milhões:**

| Natureza | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Crescimento |
|---|---|---|---|---|---|---|---|
| Imagem | 56,96 | 68,20 | 74,23 | 76,93 | 80,09 | 82,24 | +44% |
| Laboratorial | 19,43 | 24,14 | 26,59 | 28,79 | 30,61 | 32,53 | +67% |
| Funcional | 3,64 | 4,51 | 4,85 | 5,08 | 5,26 | 5,48 | +50% |
| Endoscópico | 3,25 | 3,87 | 4,57 | 5,19 | 5,12 | 5,34 | +64% |

**Discussão:** exames laboratoriais apresentam o maior crescimento da série.
Mais relevante que o crescimento acumulado é o ritmo: enquanto os exames de
imagem desaceleram após 2022, mantendo média próxima a 3% ao ano, os
laboratoriais sustentam ritmo entre 6% e 7% ao ano até 2025. A participação do
laboratorial no total classificado sobe de 23,6% para 26,4%.

Uma hipótese compatível com o padrão é a diferença de restrição de capacidade:
exames de imagem dependem de equipamento e agenda, enquanto exames
laboratoriais escalam com coleta. Os três procedimentos laboratoriais
monitorados — citopatologia cérvico-vaginal, hemoglobina glicada e pesquisa de
sangue oculto nas fezes — são exames de rastreamento, associados a programas de
prevenção. A hipótese não é testável com os dados disponíveis e é registrada
como interpretação.

**Limitação:** a classificação abrange número desigual de procedimentos por
categoria (QD-24). A comparação válida é a evolução dentro de cada categoria,
não o volume absoluto entre elas.

---

## Discussão geral

O conjunto de análises converge para três conclusões sobre o problema original.

**Volume e custo são dimensões independentes.** A ordenação dos serviços por
frequência de uso é praticamente o inverso da ordenação por despesa.
Internações ocupam a última posição em volume e a primeira em despesa;
procedimentos odontológicos fazem o percurso oposto. Decisões de portfólio
baseadas apenas em volume — ou apenas em custo — levam a conclusões opostas. O
benchmark só é útil quando apresenta as duas dimensões conjuntamente.

**O canal de contratação explica mais que o serviço.** A frequência do mesmo
produto odontológico varia 74% entre contratação individual (1,836 no pico) e
coletivo por adesão (0,990 no piso). A diferença entre canais é maior que a
diferença entre a maioria dos serviços analisados. Qualquer benchmark de
utilização que ignore o canal produz comparação inválida.

**O produto complementar apresenta perfil de risco distinto do núcleo.**
Procedimentos odontológicos combinam frequência superior à de consultas médicas
(1,40 contra 1,29) com custo unitário de R$ 19,01 — seis vezes menor que o de
um atendimento ambulatorial e 617 vezes menor que o de uma internação. No
coletivo por adesão, a variação da frequência em seis anos foi de apenas 3%. A
combinação de uso recorrente, custo baixo e previsibilidade caracteriza
exposição financeira reduzida.

**Delimitação:** as conclusões valem para o mercado regulado de odontologia no
Brasil, no período de 2020 a 2025. Extrapolar para outros serviços agregados —
assistência funeral, clubes de desconto, telemedicina avulsa — exige cautela:
carências, comportamento de uso e regulação diferem.

---

## Análises não realizadas

| # | Análise | Pergunta | Situação |
|---|---|---|---|
| A-01 | Frequência por modalidade de operadora | 5 | Viável com o modelo atual; não executada por limitação de tempo |
| A-02 | Custo por beneficiário segundo o porte | 8 | Viável; testaria a hipótese de ganho de escala |
| A-03 | Cooperativa odontológica vs. odontologia de grupo | desdobramento | Viável; isolaria o efeito do modelo societário |
| A-04 | Prevalência de agravos | adicional | Viável; os grupos F e G estão mapeados e carregados |

As quatro são executáveis sobre o modelo dimensional já construído, sem
necessidade de nova ingestão ou transformação.

**Sem resposta por limitação da fonte:** perguntas 1 e 2 (participação de
mercado por operadora) e 11 (telemedicina). Os motivos estão detalhados na
Autoavaliação do README.
