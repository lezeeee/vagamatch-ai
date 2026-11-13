"""Run interactively in your own terminal. Never paste an API key in the chat."""
import getpass
import sys
from pathlib import Path

from dotenv import set_key


def main():
    if not sys.stdin.isatty():
        print('Abra este script no seu terminal para digitar a chave sem exibi-la.')
        return 1
    print('Configuração local do VagaMatch AI — OpenAI GPT-4.1 mini')
    print('Preço consultado em 11/11/2026: US$ 0,40/1 milhão de tokens de entrada e US$ 1,60/1 milhão de saída.')
    print('Exemplo: 5 mil tokens de entrada + 2 mil de saída = cerca de US$ 0,0052 por análise.')
    print('O custo varia com o tamanho do currículo, vaga e resposta. Cada pergunta também usa a API.')
    print('O texto do currículo e da vaga será enviado à OpenAI; não salvamos o currículo no aplicativo.')
    print('Fonte: https://developers.openai.com/api/docs/models/gpt-4.1-mini')
    if input('Você aceita usar esta API paga? Digite SIM para ativar: ').strip().upper() != 'SIM':
        print('Nenhuma chamada paga foi ativada.')
        return 0
    key = getpass.getpass('Cole a chave da OpenAI (não aparecerá na tela): ').strip()
    if not key or any(char.isspace() for char in key):
        print('Chave vazia ou inválida. Nada foi alterado.')
        return 1
    env_path = Path(__file__).resolve().parent / '.env'
    set_key(env_path, 'OPENAI_API_KEY', key)
    set_key(env_path, 'VAGAMATCH_MODE', 'openai')
    set_key(env_path, 'VAGAMATCH_ALLOW_PAID_API', 'true')
    print('Configuração salva no .env local, ignorado pelo Git. Atualize a página da aplicação.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
