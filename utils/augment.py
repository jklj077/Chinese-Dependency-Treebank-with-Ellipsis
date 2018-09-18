import os
import sys

from argparse import ArgumentParser
from collections import Counter

import requests

ID = 0
FORM = 1
POS = 4
HEAD = 6
DEP = 7


class StanfordCoreNLP:
    def __init__(self, host, port):

        self.host = host
        self.port = port
        self.lang = 'zh'

        self.properties = {
            'annotators': 'tokenize,ssplit,pos,depparse',
            'outputFormat': 'conllu',
            'tokenize.language': 'Whitespace',
            'ssplit.eolonly': 'true'
        }

        self.url = self.host + ':' + str(self.port)

    def annotate(self, text):
        if sys.version_info.major >= 3:
            text = text.encode('utf-8')

        r = requests.post(
            self.url,
            params={
                'properties': str(self.properties),
                'pipelineLanguage': self.lang
            },
            data=text,
            headers={'Connection': 'close'})
        return r.text


class Token(object):
    def __init__(self, id_, form, omit, head):
        self.id = id_
        self.form = form
        self.omit = omit
        self.pos = None
        self.head = head
        self.rel = None
        self.ppos = None
        self.phead = None
        self.prel = None
        self.no_ppos = None
        self.no_phead = None
        self.no_prel = None

    def __str__(self):
        return '\t'.join([
            x if x is not None else '_' for x in [
                self.id, self.form, self.omit, self.pos, self.head, self.rel,
                self.no_ppos, self.no_phead, self.no_prel, self.ppos,
                self.phead, self.prel
            ]
        ])


def check_dep_type(fp, type_='e2e'):
    # file should not be augmented
    sent = []
    count = 0
    total = 0

    with open(fp, encoding='utf-8', mode='r') as fin:
        for line in fin:
            line = line.strip()
            if line:
                sent.append(Token(*line.split('\t')))
            else:
                if sent:
                    matched = False
                    for entry in sent:
                        if entry.head == '0':
                            continue
                        head = sent[int(entry.head) - 1]
                        if type_ == 'e2e' and entry.omit == 'I' and head.omit == 'I':
                            matched = True
                            print('{} -> {}'.format(head.form, entry.form))
                        elif type_ == 'e2o' and entry.omit == 'O' and head.omit == 'I':
                            matched = True
                            print('{} -> {}'.format(head.form, entry.form))
                        elif type_ == 'o2e' and entry.omit == 'I' and head.omit == 'O':
                            matched = True
                            print('{} -> {}'.format(head.form, entry.form))
                        elif type_ == 'o2o' and entry.omit == 'O' and head.omit == 'O':
                            matched = True
                            print('{} -> {}'.format(head.form, entry.form))
                    if matched:
                        count += 1
                    total += 1
                    sent = []

    print('matched ({}): {}/{}'.format(type_, count, total))


mapping = {
    'VA': 'ADJ',
    'VC': 'AUX',
    'VE': 'VERB',
    'VV': 'VERB',
    'NR': 'PROPN',
    'NT': 'NOUN',
    'NN': 'NOUN',
    'PN': 'PRON',
    'LC': 'ADP',
    'DT': 'DET',
    'CD': 'NUM',
    'OD': 'ADJ',
    'M': 'NOUN',
    'AD': 'ADV',
    'P': 'ADP',
    'CC': 'CCONJ',
    'CS': 'SCONJ',
    'DEC': 'PART',
    'DEG': 'PART',
    'DER': 'PART',
    'DEV': 'PART',
    'SP': 'PART',
    'AS': 'AUX',
    'ETC': 'PART',
    'MSP': 'PART',
    'IJ': 'INTJ',
    'ON': 'ADV',
    'PU': 'PUNCT',
    'JJ': 'ADJ',
    'FW': 'X',
    'LB': 'ADP',
    'SB': 'AUX',
    'BA': 'ADP'
}


def check_pos_type(fp, ud=False, type_='O'):
    # file should be augmented
    c = Counter()

    with open(fp, encoding='utf-8', mode='r') as fin:
        for line in fin:
            line = line.strip()
            if line and line[0] != '#':
                parts = line.split('\t')
                if parts[2] == type_:
                    c.update([parts[-3] if not 
                    
                    ud else mapping[parts[-3]]])

    print('POS ({})'.format(type_))
    total = 0
    for key, value in c.most_common():
        print('{}:\t{}'.format(key, value))
        total += value
    print('total: {}'.format(total))


def aug_sent(sent, nlp):
    sent_str = ' '.join([token.form for token in sent])
    res = nlp.annotate(sent_str)
    for i, line in enumerate(res.split('\n')):
        line = line.strip()
        if not line:
            break
        anns = line.split('\t')
        sent[i].ppos = anns[POS]
        sent[i].phead = anns[HEAD]
        sent[i].prel = anns[DEP]

    no_sent = [token for token in sent if token.omit != 'I']
    no_sent_str = ' '.join([token.form for token in no_sent])
    res = nlp.annotate(no_sent_str)
    for i, line in enumerate(res.split('\n')):
        line = line.strip()
        if not line:
            break
        anns = line.split('\t')
        no_sent[i].no_ppos = anns[POS]
        if anns[HEAD] != '0':
            no_sent[i].no_phead = no_sent[int(anns[HEAD]) - 1].id
        else:
            no_sent[i].no_phead = anns[HEAD]
        no_sent[i].no_prel = anns[DEP]
    return sent


def aug_file(fp, nlp):
    outp, ext = os.path.splitext(fp)
    outp = outp + '.aug' + ext
    sent = []
    with open(fp, encoding='utf-8', mode='r') as fin:
        with open(outp, mode='w', encoding='utf-8', newline='\n') as fout:
            for line in fin:
                line = line.strip()
                if line:
                    sent.append(Token(*line.split('\t')))
                else:
                    if sent:
                        aug_sent(sent, nlp)
                        fout.write('# {}\n'.format(' '.join([
                            token.form
                            if token.omit == 'O' else '_' + token.form + '_'
                            for token in sent
                        ])))
                        fout.write(''.join(
                            [str(token) + '\n' for token in sent]))
                        sent = []
                    fout.write('\n')


def main():

    argparser = ArgumentParser(
        epilog=
        'You should check the VALIDITY of the arguments. The script does not check them, and will fail with no warning.'
    )
    argparser.add_argument(
        'host',
        type=str,
        help=
        'Host address of the Stanford CoreNLP server. Do not include the trailing slash.'
    )
    argparser.add_argument(
        'port', type=int, help='Port of the Stanford CoreNLP server.')
    argparser.add_argument(
        'filepath',
        type=str,
        help=
        'Filepath of the tsv file to be augmented using Stanford CoreNLP pipeline.'
    )
    args = argparser.parse_args()

    # nlp = StanfordCoreNLP(args.host, args.port)
    # aug_file(args.filepath, nlp)

    # check_dep_type(args.filepath, type_='e2e')
    # check_dep_type(args.filepath, type_='e2o')
    check_pos_type(args.filepath, ud=True, type_='I')
    check_pos_type(args.filepath, ud=True, type_='O')


if __name__ == '__main__':
    main()
