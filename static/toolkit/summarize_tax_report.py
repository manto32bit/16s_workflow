############################################################
## summarize taxonomy report output from sintax.txt(usearch output)
##
############################################################
import os
import re

import pandas as pd


def parse_tax(tax):
    pat = '^([d,p,c,o,f,g]):(.+)\(([\.\d]+)\)$'
    m = re.match(pat, tax)
    level, name, confidence = m.groups()
    name = name.strip('"')
    return level, name, float(confidence)


def get_tax(infile,threshold):
    """
    Receive a sintax.txt file return a dict.
    :param infile:
    :return: A dict {OTU:a string of taxonomy} string is like "d:Bacteria(1.0000),p:"Proteobacteria"(1.0000),c:Alphaproteobacteria(1.0000),o:Caulobacterales(1.0000),f:Caulobacteraceae(1.0000),g:Brevundimonas(0.9900)"
    """
    tax_order = 'dpcofg'
    sintax = pd.read_csv(infile, sep='\t',header=None)
    correct_df = sintax.loc[sintax.iloc[:, 2] == '+', :]
    if correct_df.shape[0] != sintax.shape[0]:
        print("Dropping reverse matching sequence %s" % (sintax.shape[0] - correct_df.shape[0]))

    otu2tax =  {}
    for otu,tax in zip(correct_df.iloc[:, 0],
                    correct_df.iloc[:, 1]):
        rank_info = get_rank(tax)
        remained_info = {tax_rank: vals[0] for tax_rank,vals in rank_info.items() if vals[1] >=threshold}
        unclassifed_point = ''
        for idx,tax in enumerate(tax_order):
            if unclassifed_point:
                remained_info[tax] = unclassifed_point
                continue
            if tax not in remained_info and idx != 0:
                pre_tax = tax_order[idx-1]
                unclassifed_point = 'unclassfied_%s:%s' % (pre_tax,
                                                     remained_info[pre_tax].strip('"'))
                remained_info[tax] = unclassifed_point
        otu2tax[otu] = remained_info
    return otu2tax

def get_rank(tax):
    """
    Receive a string like "d:Bacteria(1.0000),p:"Proteobacteria"(1.0000),c:Alphaproteobacteria(1.0000),o:Caulobacterales(1.0000),f:Caulobacteraceae(1.0000),g:Brevundimonas(0.9900)"
    :param tax:
    :return: a dict {tax_rank:(tax_name, confidence)} like.{'d':('Bacteria',1.0000),'p':('Proteobacteria',1.0000)......}
    """
    if not tax:
        return {}
    ranks = tax.split(',')
    info = {}
    for it in ranks:
        rank, name = it.split(':')
        name, confidence = name.split('(')
        confidence = confidence.rstrip(')')
        assert rank not in info
        info[rank] = (name, float(confidence))
    return info


def summarize_tax(sintax, otutab, odir, level='gpf',threadhold=0.8):
    otu2tax = get_tax(sintax,threadhold)
    otu_df = pd.read_csv(otutab, sep='\t', index_col=0)
    # todo: if partial match, auto remove leading string.
    if otu_df.index[0] not in otu2tax:
        #     partial_match = [k for k in otu2tax.keys() if otu_df.index[0] in k]
        #     otu_df = otu_df.T
        #     if otu_df.index[0] not in otu2tax:
        #         if right_index:
        otu_df = otu_df.T
    if not os.path.isdir(odir):
        os.makedirs(odir)
    fname_template = "{prefix}_{tax}.txt"
    tax_fullname = {
        "d": "domain",
        "p": "phylum",
        "c": "class",
        "o": "order",
        "f": "family",
        "g": "genus", }
    total_otu_df = otu_df.sum(0)
    assert total_otu_df.shape[0] == otu_df.shape[1]
    otu_df = otu_df.reindex(otu2tax.keys())
    otu_df = otu_df.fillna(0)
    for tax in level:
        tax = tax.lower()
        fname = os.path.join(odir, fname_template.format(prefix=os.path.basename(otutab).split('.')[0],
                                                         tax=tax_fullname.get(tax, '')))

        group_by_df = otu_df.groupby(lambda x: otu2tax[x][tax], axis=0)
        sum_df = group_by_df.sum().T
        norm_df = sum_df.div(total_otu_df, axis=0)
        sum_df.to_csv(fname, sep='\t')
        norm_df.to_csv(fname.replace('.txt', '.norm.txt'), sep='\t')
