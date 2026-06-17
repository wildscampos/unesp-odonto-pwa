# Projeto de estudos Unesp Odontologia

Gera uma prova em PDF com 30 questoes a cada 2 dias e, no dia seguinte a cada prova, gera o PDF com gabarito e resolucao.

O foco inicial e o Vestibular Unesp/Vunesp para Odontologia em Sao Jose dos Campos. A prova diaria mistura Linguagens, Humanas, Ciencias da Natureza e Matematica, com peso maior em Biologia e Quimica por serem materias centrais para Odontologia.

## PWA para iPhone

O projeto tambem inclui um PWA em React/Vite. Ele foi pensado para iPhone 12 e uso fora da rede local.

Principios:

- nenhum servico pago de IA roda no navegador;
- a geracao por IA acontece localmente no computador via Ollama;
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

3. Instale o Ollama e baixe um modelo local para gerar questoes novas baseadas nesses PDFs:

```powershell
winget install --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
ollama pull qwen3:4b
```

O projeto usa `qwen3:4b` por padrao, gerando uma questao por vez para rodar melhor em CPU. Opcionalmente, escolha outro modelo local:

```powershell
setx OLLAMA_MODEL "qwen3:4b"
setx OLLAMA_VALIDATOR_MODEL "qwen3:4b"
```

4. Execute a acao programada do dia:

```powershell
python -m unesp_study run
```

Nas segundas, quartas e sextas, o comando gera uma prova. Os PDFs serao criados em `output/`. No PWA, a resolucao aparece imediatamente depois que a aluna finaliza a prova.

Se houver PDFs reais em `sources/`, o projeto exige Ollama rodando para gerar questoes novas. Sem PDFs, ele usa o banco local de questoes como fallback.

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

Antes de criar o PDF de resolucao, o projeto sempre valida a estrutura do gabarito salvo e tambem pode pedir uma revisao local ao Ollama para corrigir alternativa e explicacao antes de gerar o PDF.

Para usar um modelo local diferente apenas na conferencia:

```powershell
setx OLLAMA_VALIDATOR_MODEL "gemma3:12b"
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

## Custo de IA

O projeto usa IA local com Ollama. Portanto, nao ha cobranca por tokens nem custo de API.

O custo pratico e apenas o uso do computador: tempo de processamento, memoria, energia e armazenamento do modelo local. Se a geracao ficar lenta, use um modelo menor, como `gemma3:4b`; se quiser mais qualidade e o computador aguentar, teste `gemma3:12b`.

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
