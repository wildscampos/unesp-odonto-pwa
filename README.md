# Projeto de estudos Unesp Odontologia

Gera uma prova em PDF com 30 questoes a cada 2 dias e, no dia seguinte a cada prova, gera o PDF com gabarito e resolucao.

O foco inicial e o Vestibular Unesp/Vunesp para Odontologia em Sao Jose dos Campos. A prova diaria mistura Linguagens, Humanas, Ciencias da Natureza e Matematica, com peso maior em Biologia e Quimica por serem materias centrais para Odontologia.

## PWA para iPhone

O projeto tambem inclui um PWA em React/Vite. Ele foi pensado para iPhone 12 e uso fora da rede local.

Principios:

- a OpenAI API nunca roda no navegador;
- a chave fica apenas no computador/servidor que gera as provas;
- o PWA consome `web/public/data/exams.json`;
- a correcao acontece localmente ao finalizar a prova;
- respostas, progresso e historico ficam salvos no aparelho;
- o service worker cacheia o app e as provas para uso offline.

Fluxo:

```powershell
python -m unesp_study run
python -m unesp_study export-web
npm run build
```

Depois publique a pasta `dist/` em um hosting HTTPS, como Firebase Hosting, Netlify, Vercel ou GitHub Pages. No iPhone, abra a URL no Safari e use "Adicionar a Tela de Inicio".

Para testar localmente:

```powershell
npm install
npm run build
npm run preview
```

## Como usar com provas reais

1. Instale as dependencias:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

2. Baixe as provas e gabaritos anteriores da Unesp/Vunesp e coloque os PDFs em:

```text
sources/
```

Use, de preferencia, fontes oficiais. O arquivo `sources/source_manifest.json` ja lista as paginas pesquisadas. Em alguns anos, a pagina "Provas e Gabaritos" da Vunesp exige login na area do candidato; nesses casos, baixe manualmente e salve o PDF nesta pasta.

3. Configure a chave da OpenAI para gerar questoes novas baseadas nesses PDFs:

```powershell
$env:OPENAI_API_KEY="sua-chave"
```

O projeto usa `gpt-5-mini` por padrao. Opcionalmente, escolha outro modelo:

```powershell
$env:OPENAI_MODEL="gpt-5-mini"
$env:OPENAI_VALIDATOR_MODEL="gpt-5-mini"
```

4. Execute a acao programada do dia:

```powershell
python -m unesp_study run
```

Nas segundas, quartas e sextas, o comando gera uma prova. Os PDFs serao criados em `output/`. No PWA, a resolucao aparece imediatamente depois que a aluna finaliza a prova.

Sem `OPENAI_API_KEY`, o projeto roda com o banco local de questoes como fallback.

Para verificar se os PDFs reais foram carregados:

```powershell
python -m unesp_study sources
```

## Comandos uteis

Gerar prova de uma data especifica:

```powershell
python -m unesp_study exam --date 2026-06-16
```

Gerar resolucao de uma data especifica:

```powershell
python -m unesp_study answers --date 2026-06-16
```

Antes de criar o PDF de resolucao, o projeto sempre faz uma conferencia das respostas. Sem `OPENAI_API_KEY`, ele valida a estrutura do gabarito salvo. Com `OPENAI_API_KEY`, ele tambem faz uma revisao independente das 30 questoes e pode corrigir a alternativa e a explicacao antes de gerar o PDF.

Para usar um modelo diferente apenas na conferencia:

```powershell
$env:OPENAI_VALIDATOR_MODEL="gpt-5-mini"
```

Executar a acao programada do dia:

```powershell
python -m unesp_study run
```

O calendario fica em:

```text
config/study_schedule.json
```

Por padrao, a primeira prova do ciclo e `2026-06-16`, e novas provas sao geradas nas segundas, quartas e sextas.

## Custo da OpenAI

Para manter o custo baixo:

- use `gpt-5-mini`;
- nao chame OpenAI no PWA;
- gere provas apenas segunda, quarta e sexta;
- faca a correcao no app usando o gabarito ja salvo;
- use revisao por IA apenas na etapa privada de geracao quando necessario.

Estimativa com `gpt-5-mini`, 12 a 14 provas por mes:

- recomendado: cerca de US$ 0,50 a US$ 2,50/mes;
- teto operacional planejado: abaixo de US$ 3/mes na maioria dos meses;
- limite maximo aceitavel: US$ 5/mes.

O custo pode subir se muitos PDFs forem enviados como contexto integral. Se isso acontecer, reduza o tamanho de `source_context` em `src/unesp_study/sources.py` ou use resumos extraidos das provas.

## Automatizar no Windows

Abra o PowerShell nesta pasta e rode:

```powershell
.\scripts\install-daily-task.ps1 -Hour 6 -Minute 30
```

Isso cria uma tarefa chamada `UnespStudyDaily` que roda todos os dias as 06:30.

Para remover:

```powershell
Unregister-ScheduledTask -TaskName UnespStudyDaily -Confirm:$false
```

## Como a base real entra no simulado

O projeto nao copia questoes das provas anteriores. Ele usa os PDFs reais como contexto para identificar:

- materias e topicos recorrentes;
- estilo de enunciado da Unesp/Vunesp;
- nivel de dificuldade;
- tipo de habilidade cobrada;
- distribuicao adequada para uma candidata de Odontologia.

As questoes geradas sao autorais, com gabarito e resolucao.

## Onde editar as questoes de fallback

O banco fica em:

```text
src/unesp_study/data/question_bank.json
```

Cada questao tem:

- `subject`: materia
- `topic`: topico
- `prompt`: enunciado
- `options`: alternativas
- `answer`: letra correta
- `explanation`: resolucao comentada

## Fontes pesquisadas

- Portal Vestibular Unesp: `https://vestibular.unesp.br/`
- Vunesp Vestibular Unesp 2026: `https://www.vunesp.com.br/VNSP2504/`
- Vunesp Vestibular Unesp 2025: `https://www.vunesp.com.br/VNSP2404/`
- Vunesp Vestibular Unesp 2024: `https://www.vunesp.com.br/VNSP2303/`
- Vunesp Vestibular Unesp 2022: `https://www.vunesp.com.br/VNSP2105/`
- Indice secundario Brasil Escola: `https://vestibular.brasilescola.uol.com.br/downloads/universidade-estadual-paulista.htm`

## Observacao legal

As questoes deste projeto sao autorais e de treino, baseadas em analise de padroes das provas. Elas nao devem copiar enunciados, textos motivadores, imagens ou alternativas da Vunesp.
