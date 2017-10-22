#!/usr/bin/env python
# Author: Emiliano Sauvisky <esauvisky@gmail.com>.
# Description: Verifica menores preços em pesquisas do eBay periodicamente.

import sys
import argparse
import datetime
import requests
import pickle
import pprint
from bs4 import BeautifulSoup
from tendo import singleton

if __name__ == '__main__':
    # Impede a execução simultânea de mais de uma instância
    me = singleton.SingleInstance()

    # Argumentos da linha de comando
    parser = argparse.ArgumentParser(description='Verifica menores preços em pesquisas do eBay periodicamente.')
    parser.add_argument('-a', '--add-url',
                        help='adiciona a url ADD_URL ao banco de dados.')
    # TODO:
    # parser.add_argument('--auto-add', action='store_true',
    #                     help='adiciona a url na seleção primária ao banco de dados')
    parser.add_argument('--debug', action='store_true',
                        help='adiciona a url na seleção primária ao banco de dados')
    args = parser.parse_args()

    # Imprime tracebacks somente se debug está ativado
    if not args.debug:
        sys.tracebacklimit = None

    # Inicializa o dicionário de Cookies
    #   Regexp para converter cookies no formato do Netscape:
    #       Find   : .* ([^ ]+) +([^ ]+)$
    #       Replace: '\1': '\2',
    # TODO: Serializar cookies
    # TODO: Permitir importação automática de cookies no formato do Netscape
    cookies = {
        'npii':         'btguid/df0eebd715e0ab6b5521114fff9db58d5bb3edc6^cguid/' +
                        'df172dbb15e0ab1ddfe6d8cafe0cbbf95bb3edc6^',
        'ds2':          'sotr/b7pQ5zzzzzzz^',
        'ebay':         '%5Esbf%3D%2340400000f00010000060210%5Ejs%3D1%5E',
        'ns1':          'BAQAAAV7VO3kwAAaAANgAWFuz7cljODR8NjAxXjE1MDY5ODA4NTA' +
                        '3ODleXjBeMnw1fDR8N3w0Mnw0M3wxMHwzNnwxfDExXjFeNF40XjN' +
                        'eMTVeMTJeMl4xXjFeMF4wXjBeMV42NDQyNDU5MDc1gKYn8TvMKlTS8y8AUU+U9hiT9FA*',
        'dp1':          'btzo/b459d2c859^u1p/QEBfX0BAX19AQA**5bb3edc9^bl/BRen-US' +
                        '5d952149^pbf/%230000000000000100020000005bb3edc9^',
        's':            'CgAD4ACBZ1AvJZGYwZWViZDcxNWUwYWI2YjU1MjExMTRmZmY5ZGI1OGQA7gBv' +
                        'WdQLyTMGaHR0cHM6Ly93d3cuZWJheS5jb20vc2NoL2kuaHRtbD9fZnJvbT1SN' +
                        'DAmX3NhY2F0PTAmX25rdz0lMjJ1bmktdCUyMiUyMCUyMlVUMjEwRSUyMiUyMC' +
                        '1ua3RlY2gmX3BwcG49cjEmc2NwPWNlMAhGsS0*',
        'nonsession':   'CgADLAAFZ0sFROQDKACBjOLvJZGYwZWViZDcxNWUwYWI2YjU1MjExMTRmZmY5ZGI1OGROqzuc'}

    # Carrega o banco de dados
    try:
        with open('db.pickle', 'rb') as database:
            print('[eBaygent] Carregando o banco de dados...', end=' ')
            searches = pickle.load(database)
            print(str(len(searches)) + ' entradas encontradas.')
    except FileNotFoundError:
        print('[eBaygent] Atenção: o banco de dados não existe! Um novo banco de dados vazio será criado.')
        searches = []
        with open('db.pickle', 'wb') as database:
            pickle.dump(searches, database)
    except Exception as e:
        print('\n[eBaygent] Erro: ocorreu algum problema ao carregar o banco de dados:')
        sys.exit(str(e) + '\n')

    # Adiciona uma nova entrada no banco de dados
    if args.add_url:
        if any(args.add_url == search['url'] for search in searches):
            raise Exception('Erro: a entrada já existe no banco de dados!')
        else:
            print('Adicionando URL ao banco de dados...')
            searches.append({
                'url': args.add_url,
                'prices': []})

    # Retorna searches se debug estiver ativado
    if args.debug:
        print('\nDicionário das pesquisas:')
        pprint.pprint(searches["url"])
        print()

    # Faz loop pelas pesquisas e adiciona os preços atualizados
    for search in searches:
        # Faz fetch da URL usando o dicionário de cookies
        print('\n[eBaygent] Obtendo a página...')
        try:
            response = requests.get(search['url'], cookies=cookies, timeout=10)
        except Exception as e:
            print('\n[eBaygent] Erro: ocorreu algum problema ao obter a página:')
            sys.exit(str(e) + '\n')

        # Fazer uma sopa pra nóis
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.replace(' | eBay', '')
        print('[eBaygent] Termo de busca: ' + title)

        # Salva cada resposta html em um arquivo numerado
        if args.debug:
            with open(title + '.html', mode='w') as database:
                database.write(response.text)

        # Deleta os anúncios multi-preços malditos
        for priceranger in soup.select('span.prRange'):
            priceranger.find_parent('ul').decompose()

        # Retorna o primeiro anúncio encontrado
        product = soup.select('ul.lvprices')[0]

        # Extrai o preço. Somente a string da tag span, sem as tags-filhas
        price = round(float(list(product.li.span.stripped_strings)[0].strip('$')), 2)

        # Acrescenta o preço de shipping (se existente)
        try:
            shipping = round(float(list(list(product.select('li.lvshipping .ship .fee'))[0].stripped_strings)[0].replace(' shipping', '').strip('+$')), 2)
            price += shipping
            if args.debug:
                print('[eBaygent] Custo de envio: $' + str(shipping))
        except Exception:
            pass

        # Adiciona o preço à lista de preços da pesquisa
        print('[eBaygent] Último preço: $' + str(price))
        search['prices'].append((datetime.datetime.now(), price))

    # Salva no banco de dados
    print('[eBaygent] Salvando banco de dados...')
    with open('db.pickle', 'wb') as database:
        pickle.dump(searches, database)
