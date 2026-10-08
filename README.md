<div align="center">

# 📡 JobRadar
### Monitor Automatizado de Vagas de QA & Testes de Software

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Scraping-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Banco%20versionado-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Cron-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20produção-success?style=for-the-badge)

**Autora:** Liliam Kezia Oliveira Souza

</div>

---

## 💎 Proposta de valor

> Vaga boa de QA/Testes aparece pouco e some rápido — quem checa o board duas vezes por dia perde pra quem checou na primeira hora. **JobRadar** é um sistema de monitoramento contínuo que substitui essa checagem manual: varre **11 fontes** (em 2 perfis de mercado) a cada **3 horas**, filtra por cargo/cidade/mercado/idioma com três níveis de confiança, pontua cada vaga por relevância e notifica no Telegram — rodando de graça, sem servidor próprio, 24 horas por dia.

## 📄 Resumo executivo

| Achado | Número |
|---|---|
| 🌎 Perfis de mercado | **2 (Brasil + Internacional)** |
| 🔗 Fontes monitoradas | **11** (8 BR + 3 INTL) |
| ⏱️ Frequência de checagem | **a cada 3h** |
| 🔁 Rodízio de termos de busca | **sim — controla custo por ciclo** |
| 📋 Notificação imediata vs digest | **alta relevância = imediata; resto = resumo diário** |
| 💬 Feedback | **👍/👎 por botão inline no Telegram** |
| 💰 Custo de infraestrutura | **R$ 0** |

---

## 📸 Como chega pra você

As vagas chegam de duas formas:

- **🚨 Imediata:** relevância alta (acima do limiar configurado) e publicação recente — notificação individual no Telegram com motivo, nível, empresa e link.
- **📋 Digest diário:** o restante das vagas aprovadas chega num resumo único ranqueado (melhor primeiro), enviado uma vez por dia às 21h horário de Brasília. Sem virar spam.

Cada notificação tem botões **👍 / 👎** para registrar feedback — os dados ficam no banco e alimentam o relatório de precisão por fonte.

---

## 🗂️ Sumário

- [Como funciona (pipeline)](#-como-funciona-pipeline)
- [Perfis de mercado](#-perfis-de-mercado)
- [Fontes monitoradas](#-fontes-monitoradas)
- [Arquitetura técnica](#️-arquitetura-técnica)
- [Estrutura do repositório](#-estrutura-do-repositório)
- [Como rodar localmente](#-como-rodar-localmente)
- [Configuração no GitHub Actions](#-configuração-no-github-actions)
- [Testes](#-testes)

---

## 🧭 Como funciona (pipeline)

```
Cron (3h)
   │
   ├─ processar_feedback_pendente()     ← consome cliques 👍/👎 desde o último ciclo
   │
   └─ para cada Perfil (Brasil, Internacional):
         │
         ├─ _proximo_bloco_termos()     ← pega o próximo bloco do rodízio de termos
         ├─ _construir_scrapers()       ← monta lista de fontes (alta freq. todo ciclo;
         │                                 baixa freq. só 1x/dia)
         ├─ scraping paralelo           ← ThreadPoolExecutor, cada scraper isolado
         ├─ filtrar_vagas()             ← filtro em 3 níveis de confiança
         ├─ dedup (ja_vista())          ← por link e por empresa+título
         ├─ notificar / enfileirar      ← imediata se relevância ≥ limiar; senão digest
         ├─ salvar_vaga()               ← só após confirmar notificação
         ├─ _enviar_digest_diario()     ← 1x/dia, às 21h (ou forçado se atrasar 2+ dias)
         └─ _enviar_heartbeat_diario()  ← confirmação diária de que o ciclo está rodando
```

| Etapa | O que faz |
|---|---|
| **Busca** | Varre fontes em paralelo, com rodízio de termos pra não dobrar o custo ao ampliar a lista |
| **Filtra** | Cargo (forte / ambíguo + qualificador / ferramenta + cargo), cidade ou mercado remoto, idioma |
| **Pontua** | Score 0–10: cargo, ferramenta, senioridade, mercado, idioma — soma de sinais, sem IA |
| **Deduplica** | Por link e por empresa+título — pega a mesma vaga republicada em fonte diferente |
| **Notifica** | Alta relevância e publicação recente: imediata. O resto: digest diário ranqueado |
| **Aprende** | Botão 👍/👎 em cada notificação — feedback vira dado pra medir precisão por fonte e por semana |

---

## 🗺️ Perfis de mercado

O JobRadar roda **dois perfis na mesma execução**, com fontes, termos de busca e regras de filtro independentes:

| Perfil | Chave CLI | Foco | Fontes |
|---|---|---|---|
| **Brasil** | `brasil` | Vagas de QA/Testes: remoto (qualquer mercado BR/LATAM) ou híbrido/presencial na Grande São Paulo (SP, Guarulhos, ABC, Osasco, Barueri, Campinas) | LinkedIn, Gupy, Sólides, Indeed BR, Catho, GeekHunter, 99Jobs, WeWorkRemotely |
| **Internacional** | `internacional` | Vagas 100% remotas de Dados/BI em espanhol/português para mercado LATAM | LinkedIn INTL, Indeed INTL, WeWorkRemotely |

Ambos os perfis têm um **eixo secundário (Ibéria)** — vaga presencial/híbrida em Portugal ou Espanha — configurado mas atualmente desligado (ver `ATIVAR_EIXO_IBERICO` em `config.py`/`config_intl.py`).

---

## 🕸️ Fontes monitoradas

### Perfil Brasil (8 fontes)

| Fonte | Frequência | Rendimento medido |
|---|---|---|
| LinkedIn | Alta (todo ciclo) | ~8,5% — melhor fonte |
| Gupy | Alta (todo ciclo) | ~2,6% |
| Sólides | Alta (todo ciclo) | ~1,1% |
| Indeed BR | Alta (todo ciclo) | ~1,1% |
| Catho | Baixa (1x/dia) | <1%, timeout frequente |
| GeekHunter | Baixa (1x/dia) | <1% |
| 99Jobs | Baixa (1x/dia) | <1%, fonte confirmada funcionando |
| WeWorkRemotely | Baixa (1x/dia) | Sem medição própria ainda |

> **Fontes removidas:** Trampos (busca não filtra por cargo — devolve sempre o feed genérico) · Revelo (exige login, scraping público inviável)

### Perfil Internacional (3 fontes)

| Fonte | Frequência |
|---|---|
| LinkedIn INTL | Alta (todo ciclo) |
| Indeed INTL (multi-domínio) | Alta (todo ciclo) |
| WeWorkRemotely | Alta (todo ciclo) |

---

## 🏗️ Arquitetura técnica

- **Filtro em 3 níveis de confiança:** cargo inequívoco passa sozinho (ex: "QA Engineer", "SDET", "Test Automation Engineer"); cargo ambíguo (ex: "Analista de Qualidade") só conta com qualificador de QA no título (ex: "software", "automação", "selenium"); ferramenta (ex: "Cypress", "Selenium") só conta com palavra de cargo junto — nada aprova por palavra-chave solta.
- **Score de relevância sem ML:** 5 sinais (cargo, ferramenta, senioridade, mercado, idioma), pesos calibrados contra o histórico real do banco.
- **Rodízio de termos:** cada ciclo pega um bloco fixo da lista de termos, avançando de onde parou. O tamanho da lista não afeta o custo por ciclo.
- **Cadência de fontes:** fontes de baixo rendimento rodam só 1x/dia (não todo ciclo de 3h), controlando custo de Playwright/scraping.
- **Zero infraestrutura:** GitHub Actions como motor de cron, SQLite versionado no próprio Git — o histórico de vagas já vistas *é* o commit.
- **Resiliente a falhas:** nunca marca vaga como "vista" sem confirmar que a notificação saiu; alerta no Telegram se ≥50% das fontes falharem num ciclo; heartbeat diário por perfil.
- **Feedback em loop:** botão inline 👍/👎 por polling (`getUpdates`), sem webhook nem servidor. Offset salvo no banco garante que cada clique é processado exatamente uma vez.

---

## 📁 Estrutura do repositório

```
job-radar/
├── README.md
├── requirements.txt
├── main.py                  ← motor único: ciclo de busca para qualquer perfil
├── perfis.py                ← define Perfil (Brasil / Internacional) com suas fontes e regras
├── config.py                ← cargos, cidades, termos, pesos e flags do perfil Brasil
├── config_intl.py           ← equivalente para o perfil Internacional
├── job.py                   ← Job, RegrasFiltro, filtro, score de relevância
├── relatorio_precisao.py    ← aprovadas/notificadas por fonte e por semana
├── logger.py                ← configuração de log centralizada
├── teste_manual.py          ← script de inspeção pontual (fora do CI)
├── database/
│   └── database.py          ← SQLite: dedup, fila de digest, metadados, feedback
├── notifier/
│   └── telegram.py          ← notificação individual, digest, botão 👍/👎, polling
├── scrapers/
│   ├── base.py              ← classe base dos scrapers
│   ├── linkedin.py          ← LinkedIn (Brasil)
│   ├── linkedin_intl.py     ← LinkedIn (Internacional, multi-location)
│   ├── gupy.py
│   ├── indeed.py
│   ├── indeed_intl.py       ← Indeed (multi-domínio)
│   ├── solides.py
│   ├── catho.py
│   ├── geekhunter.py
│   ├── jobs99.py
│   ├── trampos.py           ← mantido mas fora do perfil (veja comentário em perfis.py)
│   └── weworkremotely_intl.py
├── utils/
│   └── filtro.py            ← filtrar_vagas(): aplica RegrasFiltro a uma lista de Job
├── tests/
│   ├── test_filtro.py       ← filtro de cargo/cidade/escopo remoto
│   ├── test_telegram.py     ← parsing de callback_data 👍/👎
│   └── test_relatorio_precisao.py
├── data/
│   └── jobs.db              ← banco SQLite versionado (histórico de dedup + metadados)
└── .github/workflows/
    ├── jobradar.yml          ← cron de produção (a cada 3h, timeout 150min)
    └── testes.yml            ← CI: roda pytest a cada push
```

---

## 💻 Como rodar localmente

```bash
git clone <repo>
cd job-radar
python -m venv venv
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Crie o arquivo `.env` na raiz:

```env
TELEGRAM_BOT_TOKEN=<token do @BotFather>
TELEGRAM_CHAT_ID=<seu chat_id>
```

Execute um ciclo completo (ambos os perfis):

```bash
python main.py --perfil brasil internacional --once
```

Ou apenas um perfil:

```bash
python main.py --perfil brasil --once
python main.py --perfil internacional --once
```

---

## ⚙️ Configuração no GitHub Actions

Os secrets do Telegram precisam ser cadastrados em **Settings → Secrets and variables → Actions** do repositório:

| Secret | Descrição |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token do bot (obtido via [@BotFather](https://t.me/BotFather)) |
| `TELEGRAM_CHAT_ID` | ID do chat que receberá as notificações |

O workflow [`jobradar.yml`](.github/workflows/jobradar.yml) já referencia esses secrets automaticamente e roda `python main.py --perfil brasil internacional --once` a cada 3 horas.

---

## 🧪 Testes

```bash
pytest tests/ -v
```

Três módulos de teste, todos rodando automaticamente a cada push via GitHub Actions:

| Arquivo | O que cobre |
|---|---|
| `test_filtro.py` | Filtro de cargo, cidade, escopo remoto — cada caso documenta um bug já corrigido |
| `test_telegram.py` | Parsing de `callback_data` do botão 👍/👎 |
| `test_relatorio_precisao.py` | Relatório de precisão por fonte e por semana |

---

<div align="center">

*Case de portfólio em automação — Python, Playwright, SQLite, GitHub Actions e engenharia de filtro sem ML. Foco em vagas de QA & Testes de Software.*

</div>
