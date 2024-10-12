import string
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from itertools import accumulate

from sklearn.metrics import confusion_matrix


def tokenize(documents, orient='dict'):
    """
    Transform documents into a collection of token

    Parameters
    -------------
    documents: list[Documents]
        A list of document objects containing
    orient: str, {'dict', 'record'}
        The  format of the returned dictionary

    Returns
    ---------
    Dict[str, Dict]
    """
    tok_map = {}
    for doc in documents:
        tokens = doc.content.split()
        end = list([e + i - 1 for i, e in
                    enumerate(accumulate([len(tok) for tok in tokens]))])
        start = [s + 2 for s in [-2] + end[:-1]]
        c = {'token': tokens, 'start': start, 'end': end}
        if orient == 'dict':
            tok_map[doc.id] = c
        elif orient == 'record':
            tok_map[doc.id] = [{'token': t, 'start': s, 'end': e} for t, s, e in
                               zip(tokens, start, end)]
        else:
            raise Exception("`orient` should be in {'dict', 'record'}")
    return tok_map


def is_punct(x):
    if x in string.punctuation:
        return True
    if x in ['-RRB-', '-LRB-']:
        return True
    return False


def compare_tags(task, untag_punct=True, min_annotators=2):
    """
    Calculate tag alignment for several annotators on the same documents

    Parameters
    -------------
    task : Task
        The task object to compute alignement from
    untag_punct : bool
        Whether or not to automatically untag punctuation tokens

    Returns
    ---------
    Dict
        Records containing the token and associated tags for each annotator
    """
    entities = {e['id']: e['title'] for e in task.entities}
    tok_map = tokenize(task.documents, orient='record')
    al = []
    for doc in task.documents:
        tokens = tok_map[doc.id]
        xl = pd.DataFrame(tokens)
        annotators = list({a.annotator for a in doc.annotations})
        if len(annotators) < min_annotators:
            continue
        for annotator in annotators:
            xl[annotator] = 'O'
        for anno in doc.annotations:
            start = anno.target['selector'][0]['startOffset']
            end = anno.target['selector'][0]['endOffset']
            idx1 = xl['start'] >= start
            idx2 = xl['end'] <= end
            xl.loc[idx1 & idx2, anno.annotator] = entities[anno.entity_id]
        if untag_punct:
            xl.loc[xl['token'].apply(is_punct), annotators] = 'O'
        al.append(xl.to_dict(orient='record'))
    return al


def filter_by_entity(al, entity, annotators):
    xl = pd.DataFrame(al)
    idx = np.array([False ]* xl.shape[0])
    for a in annotators:
        if a in xl.columns:
            idx = idx | (xl[a] == entity)
    return xl[idx]


def score(al, entity, annotators):
    df = filter_by_entity(al, entity['title'], annotators)
    annotators = [a for a in annotators if a in df.columns]
    return sum(df[annotators[0]] == df[annotators[1]]) / len(df)


def plot_confusion_matrix(
        als, task, normalize=False, title=None, cmap=plt.cm.Blues):
    xls = []
    for al in als:
        xl = pd.DataFrame(al)
        xl = xl[[a for a in xl.columns if a in task.annotators]]
        xl = xl.iloc[:, [0, 1]]
        xl.columns = ['a', 'b']
        xls.append(xl)

    cc = pd.concat(xls)
    classes = sorted(list(cc['b'].unique()))
    y_true = cc.values[:, 1]
    y_pred = cc.values[:, 0]

    if not title:
        if normalize:
            title = 'Normalized confusion matrix'
        else:
            title = 'Confusion matrix, without normalization'

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    # Only use the labels that appear in the data
#     classes = classes[unique_labels(y_true, y_pred)]
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    fig, ax = plt.subplots()
    im = ax.imshow(cm, interpolation='nearest', cmap=cmap)
    # ax.figure.colorbar(im, ax=ax)
    # We want to show all ticks...
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           # ... and label them with the respective list entries
           xticklabels=classes, yticklabels=classes,
           title=title,
           ylabel='Annotator A',
           xlabel='Annotator B')

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], fmt),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    fig.tight_layout()
    return ax
