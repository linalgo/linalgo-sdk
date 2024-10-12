import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix


def plot_confusion_matrix(y_true, y_pred, classes,
                          normalize=False,
                          title=None,
                          names=None,
                          cmap=plt.cm.Blues,
                          ax=None):

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    # Only use the labels that appear in the data
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    if ax is None:
        fig, ax = plt.subplots()
    im = ax.imshow(cm, interpolation='nearest', cmap=cmap)

    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           # ... and label them with the respective list entries
           xticklabels=classes, yticklabels=classes,
           title=title,
           ylabel=names[0],
           xlabel=names[1])

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
    return ax


def plot_matrix(cm, xlabels=None, ylabels=None, title=None, cmap=plt.cm.Blues):
    fig, ax = plt.subplots()
    im = ax.imshow(cm, interpolation='nearest', cmap=cmap)

    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=xlabels,
        yticklabels=ylabels,
        title=title
    )

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    fmt = '.2f'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], fmt),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    # fig.tight_layout()
    return ax


def multiclass_dataframe(task):
    df = []
    for annotation in task.annotations:
        data = {
            'document': annotation.document_id,
            'label': annotation.entity_id,
            'annotator': annotation.annotator,
            'created': annotation.created
        }
        df.append(data)
    df = pd.DataFrame(df)
    df['created'] = pd.to_datetime(df['created'])
    df2 = df.loc[df.groupby(['annotator', 'document']).created.idxmax()]
    df3 = df2.pivot(index='document', columns='annotator',
                    values='label').reset_index()
    annotators = [x for x in df3.columns[1:]]
    df3.columns = ['document_id'] + annotators
    df3[annotators] = df3[annotators].applymap(np.vectorize(task.get_name))

    dd = []
    for doc in task.documents:
        data = {
            'document_id': doc.id,
            'content': doc.content
        }
        dd.append(data)
    dd = pd.DataFrame(dd)
    return pd.merge(df3, dd, on='document_id')
