#!/usr/bin/env python
from bs4 import BeautifulSoup
from lxml import html
import argparse
import code
import fileinput
import json
import os.path as op
import pandas as pd
import pickle
import random
import re
import requests
import sys
from time import sleep

MAX_SCPNUM_EXCLUSIVE = 6000

format_scp_num = lambda num: str(num).zfill(3)

def generateSCPdocument(scpnum=None):
    if scpnum is None:
        scupnum = random.randint(0,MAX_SCPNUM_EXCLUSIVE)
    page = requests.get(f'http://www.scp-wiki.net/scp-{format_scp_num(scpnum)}')
    bs = BeautifulSoup(page.text, 'html.parser')
    bs_filtered_text = re.sub(r'<sup.+?>.*</sup>', '', str(bs.html))
    tree = html.fromstring(bs_filtered_text)
    content = tree.xpath('//div[@id="main-content"]//p')
    ps = ["".join(item.xpath('.//text()')) for item in content]
    if 'This page doesn\'t exist yet!' in page.text:
        return '',None
    if len(ps) == 0:
        exit('File does not exist. Please enter a valid SCP item number.')
    final = ''
    object_class = None
    for item in ps:
        if item[0:6]  == 'Item #' or \
           item[0:12] == 'Object Class' or \
           item[0:15] == 'Special Contain' or \
           item[0:11] == 'Description' or \
           item[0:8]  == 'Addendum':
                final += '-'*79 + '\n\n'
        if 'class:' in item.lower() and object_class is None:
            try: 
                object_class = re.search('class: ?(.*)', item, re.IGNORECASE).group(1).lower()
            except Exception as e:
                print(e)
                code.interact(banner='', local=globals().update(locals()) or globals(), exitmsg='')
        final += (item + "\n\n")
    if object_class == 'N':
        object_class = 'N/A'
    return (final, object_class)

def get_object_class(scpnum):
    lines, object_class = pickle.load(open('documents/SCP-' + str(format_scp_num(scpnum)) + '.txt', 'rb'))
    for l in lines:
        object_class_search = re.search('Class: ?(.+)', l, re.IGNORECASE)
        if object_class_search:
            return object_class_search.group(1)

def get_relations(scpnum, document):
    scpnum = format_scp_num(scpnum)
    document = re.sub(r'«.*»','', document)
    matches = re.findall('(?!« )SCP-(\d+)(?! »)', document, re.MULTILINE)
    return set(filter(scpnum.__ne__, matches))

def generate_graphistry():
    src = []
    dst = []
    clazz = []
    clazz_color = []
    ids = []
    edge_lbl = []
    links = []
    for scpnum in range(1, MAX_SCPNUM_EXCLUSIVE):
        filename = f'documents/SCP-{format_scp_num(scpnum)}.txt'
        full_class = None
        if op.exists(filename):
            document, full_class = pickle.load(open(filename, 'rb'))
        else:
            document, full_class = generateSCPdocument(scpnum)
            pickle.dump((document, full_class), open(filename), 'wb')
        relations = get_relations(scpnum, document)
        for relation in relations:
            src.append('SCP-'+format_scp_num(scpnum))
            dst.append('SCP-'+format_scp_num(relation))
            edge_lbl.append('')
        # full_class = get_object_class(scpnum)
        ids += ['SCP-'+format_scp_num(scpnum)]
        if full_class:
            found_class = re.search('^(\w+)', full_class)
            if found_class:
                found_class = found_class.group(1)
            else:
                found_class = 'Unknown'
            clazz += [found_class.capitalize()]
        else:
            clazz += ['Unknown']
        # clazz_color += [class2color(full_class)]
        links.append('http://www.scpwiki.com/scp-' + format_scp_num(scpnum))
    edges = pd.DataFrame({'src': src, 'dst': dst, 'lbl': edge_lbl})
    nodes = pd.DataFrame({'label': ids, 'class': clazz})
    g = graphistry
    g = g.nodes(nodes).bind(node='label', point_title='label', point_label='label')
    g = g.encode_point_color(
        'class',
        categorical_mapping={
            'Safe'        : 0xffffff00,
            'Euclid'      : 0xffffa500,
            'Keter'       : 0xffff0000,
            'Thaumiel'    : 0xffff00ff,
            'Neutralized' : 0xff00ff00,
            'Unknown'     : 0xff000000
        },
        default_mapping=0xff000000
    )
    g = g.edges(edges).bind(source='src', destination='dst', edge_label='lbl')
    # https://hub.graphistry.com/docs/api/1/rest/url/#urloptions
    g = g.settings(url_params={
            'play': 4000, 
            'linLog': True,
            'edgeOpacity': 0.50,
            # 'precisionVsSpeed': 5,
            # 'scalingRatio': 16,
            'favicon': 'http://www.scpwiki.com/local--favicon/favicon.gif',
            'dissuadeHubs': True,
            'pageTitle': 'SCP-crossreferences',
            # 'strongGravity': True,
            # 'menu': False,
            })
    g.plot()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
         description= '',
         epilog= '',
         prog= sys.argv[0],
         add_help= True,
    )
    parser.add_argument('-g' , '--graph'  , action='store_true' , help='generate graphistry graph')
    parser.add_argument('-s' , '--scrape' , action='store_true' , help='scrape wiki')
    parser.add_argument('-S' , '--single' , metavar='NUM'       , help='scrape specific scp')
    args = parser.parse_args()
    if args.graph:
        import graphistry
        from getpass import getpass
        graphistry.register(api=3, protocol='https', server='hub.graphistry.com', username='mvrozanti', password=getpass())
        generate_graphistry()
    if args.scrape:
        all_relations = {}
        for scpnum in range(1, MAX_SCPNUM_EXCLUSIVE):
            filename = f'documents/SCP-{format_scp_num(scpnum)}.txt'
            if op.exists(filename):
                document, object_class = pickle.load(open(filename, 'rb'))
            else:
                document, object_class = generateSCPdocument(scpnum)
                pickle.dump((document, object_class), open(filename, 'wb'))
                sleep(0.5) # respect the site :)
