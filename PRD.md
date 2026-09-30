# PRD — JobRadar

**Documento de Requisitos de Produto (PRD)**
**Versão:** 1.0
**Status:** Em produção
**Autora:** Liliam Kezia Oliveira Souza
**Última atualização:** Setembro 2026

---

## 1. Resumo executivo

JobRadar é um **monitor automatizado de vagas de Dados & BI** que substitui a checagem manual de boards de emprego. Ele varre **8 fontes** (com dois perfis — Brasil e Internacional) a cada **3 horas**, filtra vagas por cargo/cidade/mercado/idioma usando **três níveis de confiança**, pontua cada vaga por relevância (score 0–10, **sem ML**), deduplica e notifica via **Telegram** — rodando **24h/dia sem custo de infraestrutura** (GitHub Actions como motor de cron + SQLite versionado no Git).

**Resultado medido:** entre 07 e 15 de agosto, o sistema processou **1.052 vagas únicas** sem intervenção manual, com **73 testes automatizados** rodando em CI a cada push.

---

## 2. Contexto e problema

### 2.1 Dor do usuário

Em cidade pequena, vaga boa de Dados/BI aparece pouco e some rápido: quem checa o board duas vezes por dia perde pra quem checou na primeira hora. A checagem manual de portais de emprego é:

- **Demorada** — exige visitar vários sites, sem garantia de pegar a vaga a tempo;
- **Repetitiva** — a mesma vaga aparece republicada em várias fontes, e o candidato a reencontra como "nova";
- **Ruído alta** — a maioria das vagas de títulos genéricos ("Business Analyst") não tem relação com Dados/BI.

### 2.2 Proposta de valor

> Substituir a checagem manual por monitoramento contínuo: a vaga certa chega na hora, ranqueada por relevância, com motivo da aprovação e link — **de graça, sem servidor próprio**.

### 2.3 Público-alvo

- **Primário:** a própria autora — analista de Dados/BI no Brasil (Nordeste), buscando vaga remota ou local.
- **Secundário (extensível):** qualquer pessoa na área de Dados/BI que queira o mesmo monitoramento com outras regras de escopo (o sistema é perfilizável via `perfis.py`).

---

## 3. Objetivos e métricas de sucesso

| Objetivo | Métrica | Estado |
|---|---|---|
| Encontrar vaga relevante rápido | Latência do anúncio → notificação (`publicado_em` vs `encontrada_em`) | ⏳ `publicado_em` já coletado; relatório de latência pendente |
| Entregar só o que interessa | Taxa de aprovação por fonte (👍/👎 + `relatorio_precisao.py`) | ✅ Botão de feedback + relatório implementados; acumulando reação |
| Não poluir o Telegram | % de notificações imediatas vs. digest (limiar score ≥ 7) | ✅ ~7% imediata / ~93% digest (medido sobre ~305 vagas) |
| Não perder vaga por duplicação | % de repetição detectada por `chave_secundaria` | ✅ 23% de repetição eliminada (60 registros / 46 pares) |
| Custo zero de infraestrutura | - | ✅ R$ 0 (GitHub Actions + SQLite) |
| Confiabilidade | Heartbeat diário + alerta ≥50% de fontes falhas | ✅ Implementados |

---

## 4. Escopo

### 4.1 No escopo (v1 — atual)

- Scraping de fontes públicas de vagas de Dados/BI (8 fontes, 2 perfis).
- Filtro de **3 níveis de confiança** para cargo (forte / ambíguo+qualificador / ferramenta+cargo).
- Filtro de localização: cidade (whitelist Nordeste), remoto com validação de **escopo geográfico** e **mercado aceito**, e validação de **idioma** no perfil internacional.
- **Score de relevância 0–10** (5 sinais, pesos calibrados contra histórico real).
- **Deduplicação** por link e por empresa+título.
- **Notificação Telegram**: relevância ≥7 e vaga recente → imediata; resto → **digest diário ranqueado** (21h BRT).
- **Feedback 👍/👎** inline que vira dado de precisão.
- **Relatório de precisão** por fonte e por semana.
- **Automação e resiliência**: cron a cada 3h, heartbeat diário, alerta de saúde por fonte, proteção contra banco corrompido, backoff de push.
- Perfis **Brasil** e **Internacional** (remoto hispanofalante/lusófono global).
- 73 testes automatizados em CI.

### 4.2 Fora do escopo (v1)

- IA para compatibilidade com currículo (apenas TODO registrado — Fase 3).
- Aplicação de forma direta à vaga a partir do bot.
- Painel web/dashboard de vagas ou métricas.
- Multi-usuário / suporte a outras contas de Telegram.
- Fonte que exige login para scraping (ex.: Revelo — descartada).
- Normalização de datas relativas → absolutas para métrica de latência (parser por site, Fase 2).

---

## 5. Personas e jornada

**Persona 1 — A Analista que busca emprego (atual):**
1. Acorda e abre o Telegram; se há vaga de alta relevância, ela já chegou na hora.
2. Resto do dia: **um resumo único ranqueado** às 21h, melhor vaga no topo.
3. Ao ver vaga boa, aperta 👍; vaga fora do alvo, aperta 👎 — vira métrica de precisão.
4. Semanalmente, roda `python relatorio_precisao.py` para decidir o que ajustar no filtro.

**Persona 2 — A observadora do mercado (secundária, futura):**
- Configura um perfil próprio (cidade/termos/fontes) e usa o motor `main.py --perfil <nome>` da mesma forma.

---

## 6. Requisitos funcionais

### 6.1 Busca (RF-01)

- **RF-01.1** — Rodar 1 ciclo de busca por perfil a cada execução, com frequência de cron de 3h (configurável via `INTERVALO_MINUTOS`).
- **RF-01.2** — Rodar 8 fontes em paralelo (thread pool limitado: 4 BR / 3 Intl), cada scraper abrindo browser Playwright próprio.
- **RF-01.3** — **Rodízio de termos**: cada ciclo busca um bloco fixo de termos (`TERMOS_POR_CICLO=10`) avançando a posição no `jobs.db` (metadados), isolado por perfil — desacopla custo por ciclo do tamanho da lista de termos.
- **RF-01.4** — Fontes de **baixa frequência** rodam só na primeira execução do dia, por perfil (metadado `baixa_frequencia_ultimo_dia_*`), para não pesar no custo de todo ciclo.
- **RF-01.5** — Scraper com timeout por termo não pode derrubar o ciclo (loga e segue).

### 6.2 Filtro (RF-02)

- **RF-02.1** — **Cargo forte** (ex.: "Analista de Dados", "Data Analyst") aprova sozinho se bater no título.
- **RF-02.2** — **Cargo ambíguo** (ex.: "Business Analyst") só aprova com **qualificador de dados** junto no título (dados, sql, power bi, analytics, kpi...).
- **RF-02.3** — **Ferramenta** (ex.: "Power BI" no título) só aprova com **palavra de cargo** junto (analista, analyst, especialista...). "Desenvolvedor" fica fora de propósito.
- **RF-02.4** — Localização: cidade na whitelist (Nordeste BR) **ou** remoto confirmado por campo `modalidade` **ou** por texto de local.
- **RF-02.5** — Vaga remota **com escopo geográfico declarado** ("Remote — US only") só aprova se o escopo bater em `mercados_remoto_aceitos`; escopo não mapeado é **rejeitado** (allowlist estrita, não blocklist).
- **RF-02.6** — Desambiguação BR × EUA em "Cidade, SIGLA" (6 UFs colidem) e México (siglas estaduais).
- **RF-02.7** — Perfil internacional: remoto só, e vaga **sem mercado declarado** exige sinal de idioma (espanhol/português/LATAM) no título.
- **RF-02.8** — Título que **contradiz** modalidade remota da fonte ("Data Analyst — Hybrid") vence a classificação da fonte.
- **RF-02.9** — Normalização de texto (minúsculo, sem acento) e busca por **borda de palavra** (evita "bi" dentro de "híbrido").

### 6.3 Score de relevância (RF-03)

- **RF-03.1** — Score 0–10 por vaga aprovada, **sem ML**: soma de sinais conhecidos (cargo, ferramenta, senioridade, mercado, idioma) com pesos calibrados contra histórico real.
- **RF-03.2** — Senioridade **classifica, não filtra**; não é usada para descarte. Sênior/Especialista/Liderança pontuam negativo (acima do alvo), Júnior/Pleno pontuam teto.
- **RF-03.3** — Preenchido em `Job.relevancia` e exibido como estrelas (⭐) + motivo na notificação.

### 6.4 Deduplicação (RF-04)

- **RF-04.1** — `id` = hash da URL **sem query string** (mesma vaga com `?utm_*` não duplica).
- **RF-04.2** — `chave_secundaria` = empresa + título normalizados — pega a **mesma vaga em fontes diferentes**.
- **RF-04.3** — Migração leve e idempotente em `iniciar_db()` inclui **backfill** de colunas novas (histórico NULL não escapa da dedup).

### 6.5 Notificação (RF-05)

- **RF-05.1** — Vaga com score ≥ `LIMIAR_DIGEST_IMEDIATO` (7) **e** não-publicação-antiga → notificação **imediata**, com motivo, nível, local, modalidade, site, link e botão 👍/👎.
- **RF-05.2** — Vaga antiga ("há X meses/anos") **nunca** vai pra notificação imediata — vai pro digest mesmo com score alto (vaga estagnada pode já estar preenchida).
- **RF-05.3** — Vaga abaixo do limiar → fila `digest_pendente=1`; **digest ranqueado** 1×/dia (00:00 UTC = 21h BRT), quebra em múltiplas mensagens se passar de ~3500 caracteres.
- **RF-05.4** — Digest tem reforço: se o ciclo do horário certo falhar, envia no primeiro ciclo após 24h sem envio (não deixa fila crescer).
- **RF-05.5** — **Notifica antes de salvar** (caminho imediato): se o Telegram falhar, a vaga não é marcada "vista" e tenta no próximo ciclo.
- **RF-05.6** — Digest só limpa a fila se **todas as partes** confirmarem envio — prefere duplicar a perder vaga.
- **RF-05.7** — Eixo Ibérico (Portugal/Espanha presencial/híbrido) pode ser ativado por toggle; quando ativo, notifica com selo "exploratória". **Hoje desligado** em ambos os perfis.

### 6.6 Feedback e métricas (RF-06)

- **RF-06.1** — Botão 👍/👎 em cada notificação grava `feedback` ('positivo'/'negativo') no banco; clique re-registrado é bloqueado (teclado substituído por "✅ Registrado").
- **RF-06.2** — `processar_feedback_pendente()` consome callbacks via `getUpdates` no início de cada execução (sem webhook, com offset persistido em metadados).
- **RF-06.3** — `relatorio_precisao.py` reporta, por fonte e por semana: notificadas, avaliadas, 👍, 👎, aprovação/notificadas **e** aprovação/avaliadas (protege contra leitura errada quando há pouca reação). Sempre com banco migrado antes de ler (`iniciar_db()`).
- **RF-06.4** — `situacao` (nova/candidatei/descartei/entrevista...) como campo livre para controle de funil de candidatura; **não** entra nas taxas de precisão (medem coisas diferentes).

### 6.7 Resiliência e observabilidade (RF-07)

- **RF-07.1** — **Heartbeat diário** por perfil ("todas as fontes ok", nº de vagas novas) — se parar de chegar, o problema é o workflow, não a busca.
- **RF-07.2** — **Alerta de saúde** se ≥50% das fontes do ciclo falharem ou voltarem vazias.
- **RF-07.3** — `BancoVazioSuspeito`: banco que já existia mas veio vazio **aborta** a execução (evita notificar centenas de vagas antigas em massa).
- **RF-07.4** — Push do `jobs.db` com retry e `rebase -X theirs` (a versão do run atual sempre vence conflito — corrigido o bug de semântica inversa).
- **RF-07.5** — Logs nunca expõem token do bot nem URL com token embutido.
- **RF-07.6** — Timeout do workflow (150 min) abaixo do intervalo do cron (3h), para um run travado não empilhar no próximo.

### 6.8 Configuração e perfis (RF-08)

- **RF-08.1** — Dois perfis selecionáveis (`--perfil brasil internacional`), descritos como **dado** (fontes, termos, cidades, regras) em `perfis.py`, com lógica única em `main.py`.
- **RF-08.2** — Estado por perfil (rodízio de termos, baixa frequência, heartbeat, digest) isolado por chave de metadados com sufixo do perfil.
- **RF-08.3** — Toggles independentes para eixos secundários (Ibéria BR vs. Intl) e listas de cidades/mercados/idiomas canônicas e compartilhadas quando faz sentido (evita divergência).

---

## 7. Requisitos não funcionais

| Categoria | Requisito |
|---|---|
| **Custo** | R$ 0 de infraestrutura — GitHub Actions (cron) + SQLite versionado no Git. |
| **Disponibilidade** | Botagem por cron a cada 3h; ciclo medido entre ~1h30–2h; heartbeat evidencia parada do workflow. |
| **Performance** | Crawling em paralelo limitado (4/3 workers) para não estourar limites de worker e IP; rodízio de termos mantém custo por ciclo constante. |
| **Confiabilidade** | Nenhuma vaga marcada "vista" antes de notificada; prefere duplicar a perder; banco e migrações idempotentes. |
| **Segurança** | Token e chat id apenas via `.env`/GitHub Secrets; logs sanitizados (sem URL/token); `jobs.db` versionado contém **só dados públicos de vagas**. |
| **Extensibilidade** | Nova fonte = novo scraper + declaração no perfil; nova regra = campo em `RegrasFiltro` (dataclass com campos nomeados, evita erro de ordem de args em silêncio). |
| **Qualidade** | 73 testes em CI a cada push, cada caso documentando bug real corrigido (regressão, não cenário hipotético). |

---

## 8. Arquitetura (visão do produto)

```
┌─────────────────── GitHub Actions: cron 0 */3 * * *  ───────────────────┐
│                                                                         │
│  main.py --perfil brasil internacional --once                           │
│    │                                                                    │
│    ├─ processar_feedback_pendente()   (👍/👎 via getUpdates)             │
│    │                                                                    │
│    └─ ciclo_de_busca(perfil)  ──por perfil──                            │
│        1. Bloco de termos em rodízio (10/ciclo, offset em metadados)    │
│        2. Scrapers em threads paralelas (8 fontes, alta/baixa cadência) │
│        3. filtrar_vagas()  → 3 níveis de confiança + cidade + escopo    │
│        4. pontuar_relevancia() → score 0–10                            │
│        5. deduplicar (id URL + empresa/título)                          │
│        6. notificar ▶ imediata (score≥7, não-antiga) / digest_pendente  │
│        7. alerta de saúde + heartbeat + digest diário (00:00 UTC)       │
│    │                                                                    │
│    └─ commit data/jobs.db (retry + rebase -X theirs)                    │
└─────────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
Fonte: Gupy, LinkedIn, Solides, Indeed, Catho, GeekHunter, 99Jobs,
WeWorkRemotely (BR) + LinkedIn Intl, Indeed Intl, WeWorkRemotely (Intl)
```

Decisões de arquitetura chave:

- **Sem ML no score:** 5 sinais com pesos calibrados contra o banco real — transparência e facilidade de ajuste, volume de dados pequeno demais para modelo valer a pena.
- **Mercado ≠ costa:** `LOCATIONS_*` = onde buscar (custo); `MERCADOS_REMOTO_ACEITOS` = o que aceitar (custo zero). O filtro é **allowlist estrita**: escopo declarado não reconhecido é rejeitado.
- **Banco versionado:** o histórico de vagas já vistas *é* o commit — garante dedup entre execuções sem infraestrutura.
- **Single motor, multi-perfil:** o que muda entre mercados é dado, não lógica.

---

## 9. Riscos e mitigações

| Risco | Impacto | Mitigação atual |
|---|---|---|
| **Concentração em LinkedIn (89,5%)** | Endpoint não oficial; bloqueio derrubaria a maior parte da cobertura | Fontes secundárias paginadas mais fundo; cadência baixa onde rende pouco; alerta de saúde quando fontes falham |
| **Anti-bot/blocking (Indeed, Catho)** | Fonte volta vazia em silêncio | Timeout por termo; 0 vagas brutas = problema registrado; alerta ≥50% de fontes falhas |
| **Mudança de layout das fontes** | Scraper quebra silenciosamente | Alerta por fonte; log de funil bruta→filtrada→nova por fonte |
| **Banco corrompido/perdido** | Re-notifica vagas antigas em massa | `BancoVazioSuspeito` aborta execução |
| **Falso positivo de cargo ambíguo/ferramenta** | Ruído no Telegram | Regra de qualificador obrigatório + feedback 👍/👎 como dado |
| **Falso negativo de vaga boa (escopo)** | Vaga válida barrada | `MERCADOS_REMOTO_ACEITOS` abrangente + cidades por igualdade (não substring) |
| **Workflow para de rodar sem aviso** | Silêncio parece "sem vaga" | Heartbeat diário por perfil |

---

## 10. Roadmap / fases futuras

| Fase | Item | Status |
|---|---|---|
| **Fase 2** | Relatório de **latência** (anúncio → notificação) usando `publicado_em` | Pendente |
| **Fase 2** | Parser de datas relativas → absolutas por fonte | Pendente |
| **Fase 2** | Ampliar LOCATIONS_INTL conforme rendimento medido | Pendente |
| **Fase 3** | **Compatibilidade com currículo por IA** na notificação (`TODO` em notifier/telegram.py) | Pendente |
| **Contínuo** | Novas fontes públicas de vagas | Contínuo |
| **Contínuo** | Religar eixo Iberia quando desejado (toggles prontos) | Em standby |

---

## 11. Critérios de aceite (definição de pronto)

Para uma mudança no JobRadar ser considerada pronta:

1. **Sem vaza-de-escopo:** vaga fora do mercado/cidade/idioma configurado nunca aparece no Telegram; vaga dentro sempre aparece, mesmo em fonte diferente (dedup não esconde vaga válida).
2. **Sem notificação perdida:** vaga nova só é marcada "vista" depois de notificada (imediata) ou enfileirada (digest); falha parcial do digest re-tenta, nunca descarta.
3. **Sem ruído:** cargo ambíguo e ferramenta só passam com qualificador; título contradizendo remoto é respeitado.
4. **Testável:** novo comportamento da camada de filtro/parse tem caso em `tests/` rodando em CI.
5. **Observável:** mudanças de escopo/funil ficam visíveis em log; alertas de saúde e heartbeat seguem operando.
6. **Mensurável:** feedback 👍/👎 continua alimentando `relatorio_precisao.py` para medir se a mudança melhorou precisão por fonte.

---

## 12. Anexo — números de referência

- **1.052 vagas únicas** processadas entre 07 e 15 de agosto, sem intervenção manual.
- **89,5%** das vagas concentradas em uma única fonte (LinkedIn).
- **73 testes** automatizados, cada um documentando um bug real corrigido.
- **8 fontes** monitoradas; **3h** de cadência; **R$ 0** de custo de infra.
- **Score:** distribuição medida sobre ~305 vagas — 4 (2%), 5 (24%), 6 (67%), 7 (5%), 8 (2%) — embasou o limiar 7 para imediata vs. digest.