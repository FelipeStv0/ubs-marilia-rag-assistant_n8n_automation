"""Instrucoes seguras de importacao para o n8n migrado.

Nao executa importacao automaticamente: evita sobrescrever IDs, publicar fluxos
duplicados ou reiniciar uma instancia legado com chave exposta.
"""
import sys


def main():
    print("Instalacao automatica desabilitada apos a migracao do n8n.")
    print("Abra http://localhost:5679 e importe separadamente:")
    print(" - workflows/01-atualizacao-fontes.json")
    print(" - workflows/02-perguntas-rag.json")
    print("Revise os nos e endpoints antes de publicar.")
    print("Garanta que somente um workflow de coleta fique publicado.")
    print("Consulte docs/MIGRACAO_N8N.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
