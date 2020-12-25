#!/usr/bin/env python3
from bs4 import BeautifulSoup
from getpass import getpass
from lxml import html
import argparse
import code
import fileinput
import graphistry
import json
import os.path as op
import pandas as pd
import pickle
import random
import re
import requests
import sys

MAX_SCPNUM_EXCLUSIVE = 6000

format_scp_num = lambda num: str(num).zfill(3)

def generateSCPdocument(scpnum=None):
    if scpnum is None:
        scupnum = random.randint(0,MAX_SCPNUM_EXCLUSIVE)
    page = requests.get(f'http://www.scp-wiki.net/scp-{format_scp_num(scpnum)}')
    tree = html.fromstring(page.content)
    content = tree.xpath('//div[@id="page-content"]//p')
    ps = ["".join(item.xpath('.//text()')) for item in content]
    if 'This page doesn\'t exist yet!' in page.text:
        return ''
    if len(ps) == 0:
        exit('File does not exist. Please enter a valid SCP item number.')
    final = ''
    object_class = None
    for item in ps:
        if item[0:6] == 'Item #' or \
                item[0:12] == 'Object Class' or \
                item[0:15] == 'Special Contain' or \
                item[0:11] == 'Description' or \
                item[0:8] == 'Addendum':
                # if item[0:12] == 'Object Class':
                final += '-'*79 + '\n\n'
        final += item + '\n\n'
    return final, object_class

def generateSCPdocument2(scpnum=None):
    if scpnum is None:
        scupnum = random.randint(0,MAX_SCPNUM_EXCLUSIVE)
    page = requests.get(f'http://www.scp-wiki.net/scp-{format_scp_num(scpnum)}')
    bs = BeautifulSoup(page.text, 'html.parser')
    bs_filtered_text = re.sub(r'<sup.+?>.*</sup>', '', str(bs.html))
    tree = html.fromstring(bs_filtered_text)
    content = tree.xpath('//div[@id="page-content"]//p')
    ps = ["".join(item.xpath('.//text()')) for item in content]
    if 'This page doesn\'t exist yet!' in page.text:
        return '',None
    if len(ps) == 0:
        exit('File does not exist. Please enter a valid SCP item number.')
    final = ''
    object_class = None
    for item in ps:
        if (item[0:6] == 'Item #') or \
                (item[0:12] == 'Object Class') or \
                (item[0:15] == 'Special Contain') or \
                (item[0:11] == 'Description') or \
                (item[0:8] == 'Addendum'):
                if item[0:12] == 'Object Class':
                    try: 
                        object_class = re.search('Object Class: (.*)', item).group(1)
                    except Exception as e:
                        print(e)
                final += '-'*79 + '\n\n'
        final += (item + "\n\n")
    return (final, object_class)

# https://stackoverflow.com/questions/18453176/removing-all-html-tags-along-with-their-content-from-text
def get_object_class(scpnum):
    lines, object_class = pickle.load(open('documents/SCP-' + str(format_scp_num(scpnum)) + '.txt', 'rb'))
    for l in lines:
        object_class_search = re.search('Class: (.+)', l, re.IGNORECASE)
        if object_class_search:
            return object_class_search.group(1)

def get_relations(scpnum, document):
    scpnum = format_scp_num(scpnum)
    document = re.sub(r'«.*»','', document)
    matches = re.findall('(?!« )SCP-(\d+)(?! »)', document, re.MULTILINE)
    return set(filter(scpnum.__ne__, matches))

def to_js(relations):
    js = ''
    for scpnum, relations in relations.items():
        for relation in relations:
            js += f'g.addEdge("SCP-{scpnum}", "SCP-{relation}");\n'
    return js

# test https://graus.nu/blog/force-directed-graphs-playing-around-with-d3-js/
# test https://philogb.github.io/jit/demos.html
def generate_html():
    all_relations = {}
    for scpnum in range(1, MAX_SCPNUM_EXCLUSIVE):
        filename = f'documents/SCP-{format_scp_num(scpnum)}.txt'
        if op.exists(filename):
            document = '\n'.join(open(filename, 'r').readlines())
        else:
            document = generateSCPdocument(scpnum)
            open(filename, 'w').write(document)
        relations = get_relations(scpnum, document)
        if relations:
            all_relations[scpnum] = relations
            print(scpnum, relations)
    js = to_js(all_relations)
    lines = open('scp.html.template', 'r').readlines()
    output_lines = []
    for line in lines:
        output_lines.append(line.replace('xxx', js))
    open('scp.html', 'w').writelines(output_lines)

def to_js2(all_relations):
    data = []
    for scpnum, adjacencies in all_relations.items():
        kek = []
        for adjacency in adjacencies:
            kek.append({ 
                'nodeTo': adjacency,
                'data': {'weight':1}
                        })
        data.append({
            'id': str(scpnum),
            'name': f'SCP-{format_scp_num(scpnum)}',
            'data': {
                '$dim': 10,
                '$type': 'star'
                },
            'adjacencies': kek
            })
    return data

def generate_html2():
    all_relations = {}
    for scpnum in range(1, 500):
        filename = f'documents/SCP-{format_scp_num(scpnum)}.txt'
        if op.exists(filename):
            document = '\n'.join(open(filename, 'r').readlines())
        else:
            document = generateSCPdocument(scpnum)
            open(filename, 'w').write(document)
        relations = get_relations(scpnum, document)
        if relations:
            all_relations[scpnum] = relations
            print(scpnum, relations)
    js = to_js2(all_relations)
    open('hypertree/Jit/Examples/Hypertree/data.js', 'w').write("data='"+json.dumps(js)+"'")

def generate_graphistry():
    src = []
    dst = []
    clazz = []
    clazz_color = []
    ids = []
    edge_lbl = []
    links = []
    for scpnum in range(1, 1000):
        filename = f'documents/SCP-{format_scp_num(scpnum)}.txt'
        full_class = None
        if op.exists(filename):
            document, full_class = pickle.load(open(filename, 'rb'))
            # document = '\n'.join(open(filename, 'r').readlines())
        else:
            document, full_class = generateSCPdocument2(scpnum)
            pickle.dump((document, full_class), open(filename), 'wb')
            # open(filename, 'w').write(document)
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
            clazz += [found_class]
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
            'Safe'        : 0xff0000ff,
            'Euclid'      : 0xffffff00,
            'Keter'       : 0xffff0000,
            'Thaumiel'    : 0xffff00ff,
            'Neutralized' : 0xffffffff,
            'Unknown'     : 0xff000000
        }
    )
    g = g.edges(edges).bind(source='src', destination='dst', edge_label='lbl')
    # https://hub.graphistry.com/docs/api/1/rest/url/#urloptions
    g = g.settings(url_params={
            'play': 0, 
            'linLog': True,
            'edgeOpacity': 0.16,
            'precisionVsSpeed': 5,
            'scalingRatio': 16,
            'favicon': 'http://www.scpwiki.com/local--favicon/favicon.gif',
            'dissuadeHubs': True,
            'pageTitle': 'SCP crossreferences',
            })
    g.plot()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
         description= '',
         epilog= '',
         prog= sys.argv[0],
         add_help= True,
    )
    parser.add_argument('-g' , '--graph' , action='store_true'       , help='generate scp.html')
    parser.add_argument('-s' , '--scrape' , action='store_true'       , help='scrape wiki')
    parser.add_argument('-S' , '--single'  , metavar='NUM', help='scrape specific scp')
    args = parser.parse_args()
    if args.graph:
        graphistry.register(api=3, protocol='https', server='hub.graphistry.com', username='mvrozanti', password=getpass())
        generate_graphistry()
    if args.scrape:
        all_relations = {}
        for scpnum in range(1, MAX_SCPNUM_EXCLUSIVE):
            filename = f'documents/SCP-{format_scp_num(scpnum)}.txt'
            if op.exists(filename):
                document, object_class = pickle.load(open(filename, 'rb'))
                # document = '\n'.join(open(filename, 'r').readlines())
            else:
                document, object_class = generateSCPdocument2(scpnum)
                pickle.dump((document, object_class), open(filename, 'wb'))
