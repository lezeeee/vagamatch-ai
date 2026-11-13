# Validação — 13/11/2026

Ambiente: Windows, Python 3.11, Ollama 0.40.16, modelo local `qwen3:4b-instruct-2507-q4_K_M`. Sem API paga ou chave. PDFs fictícios gerados por `examples/create_sample.py`.

## Testes automatizados

Comando: `.venv\Scripts\python.exe -m pytest -q`.

**57 passaram.** Os transportes de IA nesses testes são simulados. Incluem agrupamento de requisitos repetidos, rejeição de categorias conflitantes, correção local limitada a uma tentativa, rejeição de frases negativas como prova positiva e ausência de troca automática para API paga.

## Inferência real

Caso com currículo fictício contendo projeto em Java/POO e a frase “Nao tenho experiencia em Python.”:

| Requisito da vaga | Resultado observado |
| --- | --- |
| Experiência profissional de 3 anos em Python | Não encontrado, sem inventar experiência |
| Java ou Kotlin | Atendido, com citação literal do projeto em Java |

A execução após o ajuste levou aproximadamente 8,5 segundos com o modelo já carregado. A saída está em `examples/negacao-local.json`. O tempo não é uma garantia para outros documentos ou computadores.

Na interface, com o PDF fictício de exemplo e a IA real:

- Java/POO: atendido, com a citação do projeto acadêmico.
- SQL/PostgreSQL: parcialmente atendido, com a citação dos exercícios em SQL.
- Python/FastAPI: não encontrado.
- O filtro exibiu apenas o requisito parcial e abriu suas evidências.
- À pergunta sobre comprovar Python sem inventar qualificações, a IA informou que o currículo não comprovava Python e sugeriu estudo e projetos futuros, com citações literais das experiências existentes.

Esse fluxo foi observado no navegador em 13/11/2026, usando o servidor local após os ajustes.

## Limites da verificação

Esses exemplos não medem a precisão geral do modelo. Uma citação literal pode receber interpretação errada. Textos longos, layouts complexos, instruções maliciosas e negações menos diretas exigem avaliação adicional. A aplicação ainda não foi hospedada na internet; o repositório de código é [lezeeee/vagamatch-ai](https://github.com/lezeeee/vagamatch-ai).
