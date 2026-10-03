\# MYRA — Tools



Cada arquivo `.py` nesta pasta é uma \*\*Tool\*\* do Open WebUI que pode ser importada manualmente ou via script.



\## Tools disponíveis



| Arquivo | Nome no Open WebUI | Função | Nº de métodos |

|---|---|---|---|

| `browseragent.py` | BrowserAgent | Navegador, email, arquivos, automação do PC | \~30 |

| `codeagent.py` | CodeAgent | Programação (gerar, explicar, refatorar, testar) | 21 |

| `visuals\_core.py` | Visuals Core | Gráficos, tabelas, heatmaps, timelines | 10 |



\## Como importar uma Tool



\### Método 1 — Manual (via UI)



1\. Abrir Open WebUI: `http://localhost:8082`

2\. \*\*Admin Settings → Tools → "+ Create New Tool"\*\*

3\. \*\*Name:\*\* nome exato da tabela acima

4\. Colar o conteúdo do arquivo `.py`

5\. \*\*Save\*\*

6\. \*\*Admin Settings → Models → Local Agent → Tools\*\* → marcar a tool

7\. \*\*Save\*\*



\### Método 2 — Automático (via API)



Rodar:

```powershell

.\\tools\\upload\\upload\_tools.ps1

