#!/usr/bin/env python3
from lxml import html
import argparse
import code
import fileinput
import random
import re
import requests
import sys
import os.path as op

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
        # exit(f'SCP-{str(scpnum).zfill(3)} does not exist yet')
        return ''
    if len(ps) == 0:
        exit('File does not exist. Please enter a valid SCP item number.')
    final = ''
    for item in ps:
        if (item[0:6] == 'Item #') or \
                (item[0:12] == 'Object Class') or \
                (item[0:15] == 'Special Contain') or \
                (item[0:11] == 'Description') or \
                (item[0:8] == 'Addendum'):
            for _ in range(79):
                final += "-"
            final += "\n\n"
        final += (item + "\n\n")
    return final

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
	    description= '',
	    epilog= '',
	    prog= sys.argv[0],
	    # usage= (generated),
	    add_help= True,
    )
    parser.add_argument('-g' , '--graph' , action='store_true'       , help='generate scp.html')
    parser.add_argument('-f' , '--file'  , help='generate scp.html')
    args = parser.parse_args()
    if args.graph:
        generate_html()
