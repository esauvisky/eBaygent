#!/usr/bin/env python3
# Author: Emiliano Sauvisky
# Description:


def initializeDatabase():
    pass


def updatePrices():
    pass


def notifyChanges():
    pass


if __name__ == '__main__':
    initializeDatabase()
    updatePrices()
    notifyChanges()

    # Uma entrada na DB por pesquisa
    # Cabeçalho: URL, Data1, Data2, ...
    # Linha 1: URL Prod1, Preco1, Preco2, ...
    # Linha 2: ...

    # Pesquisar melhor maneira de salvar este tipo de DB
    # Ver stackexchange

    # Usar o boilerplate completo
    # ou Python

    # ---- algoritmo basico ----/
    # Adicionar data ao cabecalho da DB
    # Para cada entrada/produto/linha:
    # - wget URL
    # - Extrair anúncios
    # - Para cada anúncio,
    # - -Verificar se é válido
    # - - Se for válido, break e selecionar o anúncio
    # - - Senao, continuar o loop
    # - Se nenhum anúncio foi selecionado, error exit
    # - Extrair o preço do anúncio selecionado
    # - Adicionar ao banco de dados
    pass
