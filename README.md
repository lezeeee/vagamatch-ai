# VagaMatch AI

Projeto de portfólio de **Eliese** ([lezeeee](https://github.com/lezeeee)). Compara currículo PDF e descrição de vaga usando IA, mostra requisitos com evidências e permite fazer perguntas sobre o currículo.

Código: [lezeeee/vagamatch-ai](https://github.com/lezeeee/vagamatch-ai).

**Modo padrão: IA local gratuita com Ollama + Qwen3 4B Instruct.** Não exige chave, cartão ou conta de API. Não envia currículos para serviços externos. A alternativa paga da OpenAI continua opcional e bloqueada sem configuração explícita.

## Iniciar no Windows

Pré-requisito: **Python 3.11**. Abra **`iniciar.cmd`** ou execute, nesta pasta:

```powershell
py -3.11 iniciar.py
```

Depois abra **http://127.0.0.1:8000**. Ctrl+C encerra o site.

O inicializador cria o ambiente Python e instala as dependências quando necessário. Se não encontrar o Ollama, baixa o pacote oficial, confere o SHA-256 e o extrai em `.runtime/`, ignorado pelo Git. Na primeira execução também baixa o modelo `qwen3:4b-instruct-2507-q4_K_M`. São aproximadamente 1,6 GB do pacote de runtime e 2,5 GB do modelo, além de espaço para a extração. As próximas execuções reutilizam os arquivos.

**Neste computador, o runtime, o modelo e as dependências já foram preparados.** O inicializador reutiliza o runtime e os modelos da pasta de trabalho da sessão. Em outro computador, usa `.runtime/` ou uma instalação existente do Ollama. Não é necessário levar os arquivos grandes ao GitHub.

O Ollama roda em segundo plano em `127.0.0.1:11434`. O inicializador desabilita recursos de nuvem e o histórico interativo. O processo pode permanecer em segundo plano depois de fechar o site; o modelo é descarregado da memória após inatividade. Não inicia automaticamente com o Windows.

Em Linux/macOS, instale o Ollama pelo [site oficial](https://ollama.com/download), depois execute `python3 iniciar.py`.

## Usar

1. Selecione um currículo PDF com texto selecionável.
2. Cole a descrição completa da vaga e clique em **Analisar com IA**.
3. Abra um requisito para ver a explicação, a evidência com página e a sugestão. Use **Mostrar** para filtrar categorias.
4. Em **Perguntar à IA**, faça uma pergunta, por exemplo: “O que posso explicar melhor?”.
5. **Limpar** remove o arquivo selecionado, a vaga e os resultados da tela.

A seção **Testar com um exemplo** fornece um currículo e uma vaga fictícios. Não inclua currículos reais no repositório. Cada pergunta é independente e recebe novamente o currículo e a vaga; o servidor não guarda conversa ou histórico.

## Como funciona

```text
HTML/CSS/JavaScript
  -> FastAPI recebe PDF + vaga
  -> pypdf extrai texto por página, em memória
  -> API local do Ollama executa o Qwen3 4B Instruct
  -> Pydantic valida a resposta JSON
  -> Backend confere requisitos e citações nos textos originais
  -> Interface mostra categorias, evidências e sugestões
```

O código usa uma API de IA real, servida localmente por Ollama. A comparação no modo padrão não é por palavras-chave. A configuração do modelo exige resposta conforme JSON Schema e desabilita o raciocínio visível para reduzir tempo e tamanho da resposta.

O servidor rejeita citações/páginas inexistentes, requisitos inventados, classificações conflitantes e classificação positiva sem evidência. Requisitos repetidos com a mesma categoria são agrupados, reunindo citações verificadas e preservando a ordem da vaga. Frases com negação não são aceitas como prova positiva de qualificação. Mudanças de espaço ou quebra de linha são aceitas, mas a citação apresentada é o trecho original extraído. As sugestões da análise são modelos condicionais do servidor; não preenchem qualificações novas.

Se a análise local viola essas regras, o servidor pede uma única correção ao modelo e confere tudo novamente. Se continuar inválida, retorna um erro e não mostra a análise. As duas tentativas compartilham o limite total de 180 segundos. Essa correção é exclusiva do modo local gratuito; não gera chamadas à OpenAI.

Uma citação verdadeira ainda pode ser interpretada incorretamente. Explicações e respostas são geradas por IA e exigem revisão humana. “Não encontrado” significa falta de evidência no texto recebido, não ausência de conhecimento.

## Organização

| Arquivo | Responsabilidade |
| --- | --- |
| `iniciar.py` | Preparar runtime/modelo e iniciar o site local |
| `app/main.py` | Rotas HTTP e entrega da interface |
| `app/config.py` | Provedor e configuração privada |
| `app/ai_service.py` | Chamadas à IA, instruções e validação das evidências |
| `app/models.py` | Contratos estruturados com Pydantic |
| `app/uploads.py` | Envio multipart em memória, com limite de tamanho |
| `app/pdf_reader.py` | Extração e validação do PDF |
| `app/static/` | Interface em HTML, CSS e JavaScript |
| `app/analyzer.py` | Comparador de palavras-chave usado somente no modo demo explícito |
| `tests/` | Testes locais sem dependência de um modelo real |

## API

- `GET /api/health`: informa o modo, o modelo e se a API local está disponível com o modelo instalado. Não afirma qualidade da análise nem devolve chaves.
- `POST /api/analyze`: multipart com `resume` (PDF) e `job_description` (texto). Retorna `mode`, `notice` e `results`.
- `POST /api/ask`: os mesmos campos mais `question`. Retorna `answer`, `evidence` e `mode`.
- `GET /openapi.json`: esquema das respostas.

Exemplo de item da análise:

```json
{
  "requirement": "SQL e PostgreSQL",
  "status": "parcialmente_atendido",
  "evidence": [{"page": 1, "quote": "Exercicios de consultas SQL em banco de dados."}],
  "explanation": "Há SQL, mas não há evidência de PostgreSQL.",
  "suggestion": "Revise o que falta comprovar e acrescente somente exemplos de experiências que você realmente possui."
}
```

Erros: entrada/PDF inválido (422), envio grande demais (413), IA desligada/modelo ausente (503), timeout (504) e resposta inválida (502). Não há troca automática para um serviço pago.

## Testes

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

**57 testes automatizados passaram em 13/11/2026.** Eles não fazem chamadas reais à OpenAI ou ao Ollama: usam transporte HTTP simulado para testar os contratos, rotas e validações sem custo e sem depender do hardware.

Cobertura: três categorias, páginas/citações, requisitos e evidências inventados, classificação sem prova, PDFs inválidos/vazios/com senha, limites de envio, ausência de arquivo temporário, perguntas, mensagens de erro, timeout, truncamento de saída, modo local sem fallback pago, configuração ausente e separação de dados/instruções.

A validação com o modelo real é registrada separadamente em [VALIDACAO.md](VALIDACAO.md). Não confunda HTTP simulado com inferência real.

## Privacidade e limites

- Sem banco, histórico ou analytics. O PDF e os resultados ficam em memória durante o uso; o botão **Limpar** remove os dados da tela.
- Sem gravação de currículo pela aplicação. O limite de upload fica abaixo do limite de escrita temporária do parser. O descarte em memória não é apagamento criptográfico.
- No modo local, a API é fixa em `127.0.0.1:11434`, com o modelo `qwen3:4b-instruct-2507-q4_K_M`. O aplicativo não usa serviço de nuvem nem exige chave.
- O inicializador usa o Ollama oficial `0.40.16` com `OLLAMA_NO_CLOUD=1` e `OLLAMA_NOHISTORY=1`. Modelos, bibliotecas e logs técnicos ocupam disco; currículos não são incluídos nesses arquivos pela aplicação.
- PDF de até 5 MB, 10 páginas e 40 mil caracteres extraídos. Vaga de 3 a 12 mil caracteres. Pergunta de 3 a 1.000 caracteres. Até 30 requisitos por análise.
- Não faz OCR e rejeita PDFs com senha. Colunas e layouts complexos podem alterar a extração.
- A velocidade e a qualidade dependem do hardware e do modelo. A primeira análise precisa carregar o modelo; PDFs grandes podem demorar ou exceder a janela de contexto do modelo local. Não há garantia de correção semântica ou cobertura de todos os requisitos.
- Não calcula nota, probabilidade, ranking ou decisão de contratação. Não comprova a veracidade de um currículo.
- Uso em `127.0.0.1`. Antes de publicar: isolamento do parser com limites de CPU/memória, timeout de extração, controle de acesso e limites de concorrência. Hospedagem com IA local precisa de recursos de computação próprios; não foi publicada nesta etapa.
- Qwen3 4B Instruct tem licença Apache 2.0. O pacote e os modelos são obtidos das fontes oficiais; não ficam versionados no repositório.

## Provedores opcionais

O padrão é `VAGAMATCH_MODE=ollama`. `iniciar.py` força esse modo e desabilita o uso pago.

Para estudar o fluxo de palavras-chave, use `VAGAMATCH_MODE=demo` ao iniciar o Uvicorn diretamente. A interface identifica a demonstração e não oferece perguntas à IA.

A integração anterior com OpenAI foi preservada, porém não está ativa. Para usá-la no futuro é necessário decidir explicitamente sobre custos, configurar uma chave privada e iniciar o Uvicorn diretamente com o modo `openai`. Não há fallback automático. As condições e preços precisam ser revisados antes de ativar. `configurar_api.py` continua disponível apenas para essa alternativa paga.

## Para explicar em entrevista

“Construí uma API FastAPI que recebe um currículo PDF e uma descrição de vaga, extrai o texto e consulta uma API de IA local. O modelo responde em JSON estruturado, e o servidor confere se as citações existem nas páginas indicadas. A interface permite filtrar requisitos e fazer perguntas. Escolhi o modo local para evitar cobrança de API e não enviar currículos para terceiros. Separei extração, integração e apresentação para permitir a troca do provedor. Testei as validações com HTTP simulado e verifico a inferência real separadamente.”

## Próximas etapas

1. Avaliar a qualidade com exemplos fictícios e anonimizados, incluindo negações e requisitos ausentes.
2. Expandir os exemplos de avaliação no repositório, usando apenas dados fictícios ou anonimizados.
3. Validar uma forma de hospedagem antes de publicar a aplicação.
4. Considerar PostgreSQL em outra versão, com decisão sobre retenção e consentimento.

Referências: [API do Ollama](https://docs.ollama.com/api/chat), [respostas estruturadas](https://docs.ollama.com/capabilities/structured-outputs), [Qwen3 4B Instruct](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M), [FastAPI](https://fastapi.tiangolo.com/), [pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
