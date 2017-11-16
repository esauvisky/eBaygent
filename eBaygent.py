#!/usr/bin/env python
# Author: Emiliano Sauvisky <esauvisky@gmail.com>.
# Description: Verifica menores preços em pesquisas do eBay periodicamente.

import os
import sys
import argparse
import datetime
import requests
import pickle
import pprint
#from subprocess import call
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify
from bs4 import BeautifulSoup
from tendo import singleton


#### Código Principal
if __name__ == '__main__':
    ## Impede a execução simultânea de mais de uma instância
    me = singleton.SingleInstance()

    ## Argumentos da linha de comando
    parser = argparse.ArgumentParser(description='Verifica menores preços em pesquisas do eBay periodicamente.')
    parser.add_argument('-a', '--add-url',
                        help='adiciona a url ADD_URL ao banco de dados.')
    # TODO: Adicionar direto da seleção primária ou clipboard
    # parser.add_argument('--auto-add', action='store_true',
    #                     help='adiciona a url na seleção primária ao banco de dados')
    parser.add_argument('-d', '--delete-url',
                        help='remove a url DELETE_URL do banco de dados.')
    parser.add_argument('--debug', action='store_true',
                        help='aumenta o nível de verbosidade para debug.')
    args = parser.parse_args()

    ## Imprime tracebacks somente se debug está ativado
    if not args.debug:
        sys.tracebacklimit = None

    ## Inicia libnotify
    Notify.init('eBaygent')

    ## Muda o diretório atual para o diretório de trabalho do eBaygent
    dir = os.path.dirname(os.path.abspath(__file__))
    #print('Diretório de trabalho: ' + dir)
    os.chdir(dir)

    ## Carrega o dicionário de Cookies
    try:
        with open('cookies.pickle', 'rb') as cookies_database:
            print('[eBaygent] Carregando cookies...')
            cookies = pickle.load(cookies_database)
    except Exception as e:
        print('[eBaygent] Erro: ocorreu algum problema ao carregar os cookies:')
        del me  # Fix para tendo.singleton
        sys.exit(str(e) + '\n')

    ## Carrega o banco de dados
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
        del me  # Fix para tendo.singleton
        sys.exit(str(e) + '\n')

    ## Adiciona uma nova entrada no banco de dados
    if args.add_url:
        if any(args.add_url == search['url'] for search in searches):
            raise Exception('Erro: a entrada já existe no banco de dados!')
        else:
            print('Adicionando URL ao banco de dados...')
            searches.append({
                'url': args.add_url,
                'prices': []})

    ## Imprime searches[] se debug estiver ativado
    if args.debug:
        print('\nDicionário das pesquisas:')
        pprint.pprint(searches)
        print()

    ## Faz loop pelas pesquisas e adiciona os preços atualizados
    for search in searches:
        ## Faz fetch da URL usando o dicionário de cookies
        print('\n[eBaygent] Obtendo a página...')
        try:
            response = requests.get(search['url'], cookies=cookies, timeout=30)
        except Exception as e:
            print('\n[eBaygent] Erro: ocorreu algum problema ao obter a página:')
            del me  # Fix para tendo.singleton
            sys.exit(str(e) + '\n')

        ## Fazer uma sopa pra nóis
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.replace(' | eBay', '')
        print('[eBaygent] Termo de busca: ' + title)

        ## Salva cada resposta html em um arquivo numerado
        if args.debug:
            with open(title + '.html', mode='w') as database:
                database.write(response.text)

        ## Deleta os anúncios multi-preços malditos
        for priceranger in soup.select('span.prRange'):
            priceranger.find_parent('ul').decompose()

        ## Retorna o primeiro anúncio encontrado
        product = soup.select('ul.lvprices')[0]

        ## Extrai o preço. Somente a string da tag span, sem as tags-filhas
        price = float(list(product.li.span.stripped_strings)[0].strip('$'))

        ## Acrescenta o preço de shipping (se existente)
        try:
            shipping = float(list(list(product.select('li.lvshipping .ship .fee'))[0].stripped_strings)[0].replace(' shipping', '').strip('+$'))
            #if args.debug:
            print('[eBaygent] Custo produto : $' + str(price))
            print('[eBaygent] Custo de envio: $' + str(shipping))
            price = round(price + shipping, 2)
        except Exception:
            price = round(price, 2)

        ## Adiciona o preço à lista de preços da pesquisa
        print('[eBaygent] Último preço: $' + str(price))
        search['prices'].append((datetime.datetime.now(), price))

        ## Verifica se há um produto mais barato e notifica o usuário
        last1Price = search['prices'][-1][1]
        last2Price = search['prices'][-2][1]
        last3Price = search['prices'][-3][1]
        # Histerese para evitar anúncios intermitentes
        if last1Price == last2Price:
            # Se o último preço for menor que 95% do preço anterior
            if last1Price <= (last3Price * 0.95):
                print('[eBaygent] Um produto mais barato foi encontrado!')
                print('[eBaygent] Preço antigo: $' + str(last3Price))
                print('[eBaygent] Preço novo  : $' + str(last1Price))
                print('[eBaygent] URL: ' + search['url'])
                # Cria a notificação
                notification = Notify.Notification.new(title + ' tem um produto mais barato! :D',
                                                       'URL: ' + search['url'] + '\n\n'
                                                       'Preço antigo: $' + str(last3Price) + '\t' +
                                                       'Preço novo  : $' + str(last1Price),
                                                       'price_down.png')

                # Seta a urgência máxima
                notification.set_urgency(2)
                # Mostra a notificação
                notification.show()
            # Se o último preço for maior que 105% do preço anterior
            elif last1Price >= (last3Price * 1.05):
                print('[eBaygent] O produto mais barato agora está mais caro.')
                print('[eBaygent] Preço antigo: $' + str(last3Price))
                print('[eBaygent] Preço novo  : $' + str(last1Price))
                print('[eBaygent] URL: ' + search['url'])
                # Cria a notificação
                notification = Notify.Notification.new(title + ' ficou mais caro... :(',
                                                       'URL: ' + search['url'] + '\n\n'
                                                       'Preço antigo: $' + str(last3Price) + '\t' +
                                                       'Preço novo  : $' + str(last1Price),
                                                       'price_up.png')
                # Seta a urgência padrão
                notification.set_urgency(1)
                # Mostra a notificação
                notification.show()

    ## Salva no banco de dados
    print('\n[eBaygent] Salvando banco de dados...')
    with open('db.pickle', 'wb') as database:
        pickle.dump(searches, database)

    ## Termina o objeto do libnotify
    # FIXME: gera alertas Glib-Gobject
    #Notify.uninit()

    ## Bodge para não exibir exception de tendo.singleton
    del me
