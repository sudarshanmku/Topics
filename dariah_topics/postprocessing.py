"""
Postprocessing Text Data, Saving Matrices, Corpora and LDA Models
*****************************************************************

Functions of this module are for **postprocessing purpose**. You can save \
`document-term matrices <https://en.wikipedia.org/wiki/Document-term_matrix>`_, \
`tokenized corpora <https://en.wikipedia.org/wiki/Tokenization_(lexical_analysis)>`_ \
and `LDA models <https://en.wikipedia.org/wiki/Latent_Dirichlet_allocation>`_, \
access topics, topic probabilites for documents, and word probabilities \
for each topic. All matrix variants provided in :func:`preprocessing.create_document_term_matrix()`_ \
are supported, as well as `lda <https://pypi.python.org/pypi/lda>`_, `Gensim <https://radimrehurek.com/gensim/>`_ \
and `MALLET <http://mallet.cs.umass.edu/topics.php>`_ models or output, respectively. \
Recurrent variable names are based on the following conventions:

    * ``topics`` means a pandas DataFrame containing the top words for each \
    topic and any Dirichlet parameters.
    * ``document_topics`` means a pandas DataFrame containing topic proportions per \
    document, at the end of the iterations.
    * ``word_weights`` means unnormalized weights for every topic and word type.
    * ``keys`` means the top *n* tokens of a topic.

Contents
********
    * :func:`doc2bow()`
    * :func:`save_document_term_matrix()` writes a document-term matrix to a `CSV <https://en.wikipedia.org/wiki/Comma-separated_values>`_
    file or to a `Matrix Market <http://math.nist.gov/MatrixMarket/formats.html#MMformat>`_ file, respectively.
    * :func:`save_model()` saves a LDA model (except MALLET models, which will be saved \
    by specifying a parameter of :func:`mallet.create_mallet_model()`).
    * :func:`save_tokenized_corpus()` writes tokens of a tokenized corpus to plain text \
    files per document.
    * :func:`show_document_topics()` shows topic probabilities for each document.
    * :func:`show_topics()` shows topics generated by a LDA model.
    * :func:`show_word_weights()` shows word probabilities for each topic.
"""
import itertools
import operator
import os
import numpy as np
import pandas as pd
import pickle
import logging

log = logging.getLogger(__name__)


def doc2bow(document_term_matrix):
    """Creates a `doc2bow` pandas Series for Gensim.

    With this function you can create a `doc2bow` pandas Series as input for Gensim, e.g. \
    to instantiate the :class:`gensim.models.LdaModel` class or get topic distributions \
    with :func:`gensim.models.LdaModel.get_document_topics()`.

    Args:
        document_term_matrix (pandas.DataFrame): A document-term matrix **designed
            for large corpora**.

    Returns:
        List of lists containing tuples.
    
    Todo:
        * Improve efficiency.

    Example:
        >>> from dariah_topics import preprocessing
        >>> tokenized_corpus = [['this', 'is', 'document', 'one'], ['this', 'is', 'document', 'two']]
        >>> document_labels = ['document_one', 'document_two']
        >>> document_term_matrix, _, _ = preprocessing.create_document_term_matrix(tokenized_corpus, document_labels, True)
        >>> isinstance(doc2bow(document_term_matrix), pd.Series)
        True
    """
    doc2bow = pd.Series()
    for n, document in enumerate(document_term_matrix.index.groupby(document_term_matrix.index.get_level_values('document_id'))):
        doc2bow[str(n)] = [(token, freq) for token, freq in zip(document_term_matrix.loc[document].index, document_term_matrix.loc[document][0])]
    return doc2bow


def save_document_term_matrix(document_term_matrix, path, document_ids=None, type_ids=None, matrix_market=False):
    """Saves document-term matrix.
    
    Writes a ``document_term_matrix`` and, in case of a large corpus matrix, \
    ``document_ids`` and ``type_ids``, which have to be specified, to comma-separated \
    values (CSV) files. Furthermore, if ``document_term_matrix`` is designed for \
    large corpora and ``matrix_market`` is True, the matrix will be saved in the \
    `Matrix Market format <http://math.nist.gov/MatrixMarket/formats.html#MMformat>`_ (`.mm`). \
    Libraries like `scipy <https://www.scipy.org>`_ and `gensim <https://radimrehurek.com/gensim/>`_ \
    are able to read and process the Matrix Market format.
    Use the function :func:`preprocessing.create_document_term_matrix()` to create a
    document-term matrix.

    Args:
        document_term_matrix (pandas.DataFrame): Document-term matrix with rows
            corresponding to ``document_labels`` and columns corresponding to types
            (unique tokens in the corpus). The single values of the matrix are
            type frequencies. Will be saved as ``document_term_matrix.csv`` or
            ``document_term_matrix.mm``, respectively.
        path (str): Path to the output directory.
        document_ids (dict, optional): Dictionary containing ``document_labels`` as
            keys and an unique identifier as value. Only required, if
            ``document_term_matrix`` is designed for large corpora. Will be saved
            as ``document_ids.csv``. Defaults to None.
        type_ids (dict, optional): Dictionary containing types as keys and an
            unique identifier as value. Only required, if ``document_term_matrix``
            is designed for large corpora. Will be saved as ``type_ids.csv``. Defaults
            to None.
        matrix_market (bool, optional): If True, matrix will be saved in Matrix
            Market format. Only for the large corpus variant of ``document_term_matrix``
            available. Defaults to False.

    Returns:
        None.

    Example:
        >>> from dariah_topics import preprocessing
        >>> import os
        >>> path = 'tmp'
        >>> tokenized_corpus = [['this', 'is', 'document', 'one'], ['this', 'is', 'document', 'two']]
        >>> document_labels = ['document_one', 'document_two']
        >>> document_term_matrix = preprocessing.create_document_term_matrix(tokenized_corpus, document_labels)
        >>> save_document_term_matrix(document_term_matrix=document_term_matrix, path=path)
        >>> preprocessing.read_document_term_matrix(os.path.join(path, 'document_term_matrix.csv')) #doctest +NORMALIZE_WHITESPACE
                      this   is  document  two  one
        document_one   1.0  1.0       1.0  0.0  1.0
        document_two   1.0  1.0       1.0  1.0  0.0
        >>> document_term_matrix, document_ids, type_ids = preprocessing.create_document_term_matrix(tokenized_corpus, document_labels, True)
        >>> save_document_term_matrix(document_term_matrix, path, document_ids, type_ids)
        >>> isinstance(preprocessing.read_document_term_matrix(os.path.join(path, 'document_term_matrix.csv')), pd.DataFrame)
        True
    """
    if not os.path.exists(path):
        log.info("Creating directory {} ...".format(path))
        os.makedirs(path)
    if not matrix_market:
        log.info("Saving document_term_matrix.csv to {} ...".format(path))
        document_term_matrix.to_csv(os.path.join(path, 'document_term_matrix.csv'))
    if isinstance(document_term_matrix.index, pd.MultiIndex) and not matrix_market:
        if document_ids and type_ids is not None:
            log.info("Saving document_ids.csv to {} ...".format(path))
            pd.Series(document_ids).to_csv(os.path.join(path, 'document_ids.csv'))
            log.info("Saving type_ids.csv to {} ...".format(path))
            pd.Series(type_ids).to_csv(os.path.join(path, 'type_ids.csv'))
        else:
            raise ValueError("You have to pass document_ids and type_ids as parameters.")
    elif isinstance(document_term_matrix.index, pd.MultiIndex) and matrix_market:
        _save_matrix_market(document_term_matrix, path)
    return None


def save_model(model, filepath):
    """Saves a LDA model.

    With this function you can save a LDA model using :module:`pickle`. If you want \
    to save MALLET models, you have to specify a parameter of the function :func:`mallet.create_mallet_model()`.

    Args:
        model: Fitted LDA model produced by `Gensim <https://radimrehurek.com/gensim/>`_
            or `lda <https://pypi.python.org/pypi/lda>`_.
        filepath (str): Path to LDA model, e.g. ``/home/models/model.pickle``.

    Returns:
        None.

    Example:
        >>> from lda import LDA
        >>> from gensim.models import LdaModel
        >>> from dariah_topics import preprocessing
        >>> save_model(LDA, 'model.pickle')
        >>> preprocessing.read_model('model.pickle') == LDA
        True
        >>> save_model(LdaModel, 'model.pickle')
        >>> preprocessing.read_model('model.pickle') == LdaModel
        True
    """
    with open(filepath, 'wb') as file:
        pickle.dump(model, file, protocol=pickle.HIGHEST_PROTOCOL)
    return None


def save_tokenized_corpus(tokenized_corpus, document_labels, path):
    """Writes a tokenized corpus to text files.

    With this function you can write tokens of a `tokenized_corpus` to plain text \
    files per document to ``path``. Every file will be named after its ``document_label``. \
    Depending on the used tokenizer, ``tokenized_corpus`` does normally not contain \
    any punctuations or one-letter words.
    Use the function :func:`preprocessing.tokenize()` to tokenize a corpus.

    Args:
        tokenized_corpus (list): Tokenized corpus containing one or more
            iterables containing tokens.
        document_labels (list): Name of each `tokenized_document` in `tokenized_corpus`.
        path (str): Path to the output directory.
    
    Returns:
        None

    Example:
        >>> tokenized_corpus = [['this', 'is', 'a', 'tokenized', 'document']]
        >>> document_labels = ['document_label']
        >>> path = 'tmp'
        >>> save_tokenized_corpus(tokenized_corpus, document_labels, path)
        >>> with open(os.path.join(path, 'document_label.txt'), 'r', encoding='utf-8') as file:
        ...     file.read()
        'this\\nis\\na\\ntokenized\\ndocument'
    """
    log.info("Saving tokenized corpus to {} ...".format(path))
    if not os.path.exists(path):
        log.info("Creating directory {} ...".format(path))
        os.makedirs(path)

    for tokenized_document, document_label in zip(tokenized_corpus, document_labels):
        log.debug("Current file: {}".format(document_label))
        with open(os.path.join(path, '{}.txt'.format(document_label)), 'w', encoding='utf-8') as file:
            file.write('\n'.join(tokenized_document))
    return None


def show_document_topics(topics, model=None, document_labels=None, doc_topics_file=None, doc2bow=None, num_keys=3, easy_file_format=True):
    """Shows topic distribution for each document.
    
    With this function you can show the topic distributions for all documents in a pandas DataFrame. \
    For each topic, the top ``num_keys`` keys will be considered. If you have a
    * `lda <https://pypi.python.org/pypi/lda>`_ model, you have to pass the model \
    as ``model`` and the document-term matrix vocabulary as ``vocabulary``.
    * `Gensim <https://radimrehurek.com/gensim/>`_ model, you have to pass only the model \
    as ``model``.
    * `MALLET <http://mallet.cs.umass.edu/topics.php>`_ based workflow, you have to\
    pass only the ``doc_topics_file``.
    
    Args:
        topics (pandas.DataFrame, optional): Only for lda models. A pandas DataFrame
            containing all topics.
        model (optional): lda or Gensim model.
        document_labels (list, optional): An list of all document labels.
        doc_topics_file (str, optional): Only for MALLET. Path to the doc-topics file.
        doc2bow (list, optional): A list of lists containing tuples of ``type_id`` and
            frequency.
        num_keys (int, optional): Number of top keys for each topic.
    
    Returns:
        A pandas DataFrame with rows corresponding to topics and columns corresponding
            to keys.

    Example:
    """
    from lda.lda import LDA
    from gensim.models import LdaModel, LdaMulticore
  
    index = [' '.join(keys[:num_keys]) for keys in topics.values]
    if isinstance(model, LDA):
        return _show_lda_document_topics(model, document_labels, index)
    elif isinstance(model, LdaModel) or isinstance(model, LdaMulticore):
        return _show_gensim_document_topics(doc2bow, model, document_labels, index)
    elif doc_topics_file is not None:
        return _show_mallet_document_topics(doc_topics_file, index, easy_file_format)


def show_topics(model=None, vocabulary=None, topic_keys_file=None, num_keys=10):
    """Shows topics of LDA model.
    
    With this function you can show all topics of a LDA model in a pandas DataFrame. \
    For each topic, the top ``num_keys`` keys will be considered. If you have a
    * `lda <https://pypi.python.org/pypi/lda>`_ model, you have to pass the model \
    as ``model`` and the document-term matrix vocabulary as ``vocabulary``.
    * `Gensim <https://radimrehurek.com/gensim/>`_ model, you have to pass only the model \
    as ``model``.
    * `MALLET <http://mallet.cs.umass.edu/topics.php>`_ based workflow, you have to\
    pass only the ``topic_keys_file``.
    
    Args:
        model (optional): lda or Gensim model.
        vocabulary (list, optional): Only for lda. The vocabulary of the 
            document-term matrix.
        topic_keys_file (str): Only for MALLET. Path to the topic keys file.
        num_keys (int, optional): Number of top keys for each topic. 
    
    Returns:
        A pandas DataFrame with rows corresponding to topics and columns corresponding
            to keys.

    Example:
    """
    from lda.lda import LDA
    from gensim.models import LdaModel, LdaMulticore
    
    if isinstance(model, LDA):
        return _show_lda_topics(model, vocabulary, num_keys)
    elif isinstance(model, LdaModel) or isinstance(model, LdaMulticore):
        return _show_gensim_topics(model, num_keys)
    elif topic_keys_file is not None:
        return _show_mallet_topics(topic_keys_file)


def show_word_weights(word_weights_file, num_tokens):
        """Read Mallet word_weigths file

        Description:
            Reads Mallet word_weigths into pandas DataFrame.

        Args:
            word_weigts_file: Word_weights_file created with Mallet

        Returns: Pandas DataFrame
        
        Todo:
            * Adapt for ``lda`` and ``gensim`` output.

        Example:
            >>> import tempfile
            >>> with tempfile.NamedTemporaryFile(suffix='.txt') as tmpfile:
            ...     tmpfile.write(b'0\\tthis\\t0.5\\n0\\tis\\t0.4\\n0\\ta\\t0.3\\n0\\tdocument\\t0.2') and True
            ...     tmpfile.flush()
            ...     show_word_weights(tmpfile.name, 2) #doctest: +NORMALIZE_WHITESPACE
            True
                document token  weight
            0         0  this     0.5
            1         0    is     0.4

        """
        word_weights = pd.read_table(word_weights_file, header=None, sep='\t', names=['document', 'token', 'weight'])
        return word_weights.sort_values('weight', ascending=False)[:num_tokens]


def _grouper(n, iterable, fillvalue=None):
    """Collects data into fixed-length chunks or blocks.
    
    This private function is wrapped in :func:`_show_mallet_document_topics()`.

    Args:
        n (int): Length of chunks or blocks
        iterable (object): Iterable object
        fillvalue (boolean): If iterable can not be devided into evenly-sized chunks fill chunks with value.

    Returns: n-sized chunks

    """
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def _show_gensim_document_topics(doc2bow, model, document_labels, index):
    """Creates a document-topic-matrix.
    
    Description:
        With this function you can create a doc-topic-maxtrix for gensim 
        output. 

    Args:
        corpus (mmCorpus): Gensim corpus.
        model: Gensim LDA model
        doc_labels (list): List of document labels.

    Returns: 
        Doc_topic-matrix as DataFrame
    
    Example:
        >>> from gensim.models import LdaModel
        >>> from gensim.corpora import Dictionary
        >>> document_labels = ['document_one', 'document_two']
        >>> tokenized_corpus = [['this', 'is', 'the', 'first', 'document'], ['this', 'is', 'the', 'second', 'document']]
        >>> id2word = Dictionary(tokenized_corpus)
        >>> corpus = [id2word.doc2bow(document) for document in tokenized_corpus]
        >>> model = LdaModel(corpus=corpus, id2word=id2word, iterations=1, passes=1, num_topics=2)
        >>> topics = _show_gensim_topics(model, 5)
        >>> index = [' '.join(keys[:2]) for keys in topics.values]
        >>> isinstance(_show_gensim_document_topics(corpus, model, document_labels, index), pd.DataFrame)
        True
    """
    num_topics = model.num_topics
    num_documents = len(document_labels)
    document_topics = np.zeros((num_topics, num_documents))

    for n, document in enumerate(doc2bow):
        for distribution in model.get_document_topics(document):
            document_topics[distribution[0]][n] = distribution[1]
    return pd.DataFrame(document_topics, index=index, columns=document_labels)


def _show_gensim_topics(model, num_keys=10):
    """Converts gensim output to DataFrame.

    Description:
        With this function you can convert gensim output (usually a list of
        tuples) to a DataFrame, a more convenient datastructure.

    Args:
        model: Gensim LDA model.
        num_keys (int): Number of top keywords for topic.

    Returns:
        DataFrame.

    ToDo:

    Example:
        >>> from gensim.models import LdaModel
        >>> from gensim.corpora import Dictionary
        >>> tokenized_corpus = [['this', 'is', 'the', 'first', 'document'], ['this', 'is', 'the', 'second', 'document']]
        >>> id2word = Dictionary(tokenized_corpus)
        >>> corpus = [id2word.doc2bow(document) for document in tokenized_corpus]
        >>> model = LdaModel(corpus=corpus, id2word=id2word, iterations=1, passes=1, num_topics=2)
        >>> isinstance(_show_gensim_topics(model, 5), pd.DataFrame)
        True
    """
    log.info("Accessing topics from Gensim model ...")
    topics = []
    for n, topic in model.show_topics(formatted=False, num_words=num_keys):
        topics.append([key[0] for key in topic])
    index = ['Topic {}'.format(n) for n in range(len(topics))]
    columns = ['Key {}'.format(n) for n in range(num_keys)]
    return pd.DataFrame(topics, index=index, columns=columns)


def _show_lda_document_topics(model, document_labels, index):
    """Creates a doc_topic_matrix for lda output.
    
    Description:
        With this function you can convert lda output to a DataFrame, 
        a more convenient datastructure.
        Use 'lda2DataFrame()' to get topics.
        
    Note:

    Args:
        model: Gensim LDA model.
        topics: DataFrame.
        doc_labels (list[str]): List of doc labels as string.

    Returns:
        DataFrame

    Example:
        >>> import lda
        >>> from dariah_topics import preprocessing
        >>> tokenized_corpus = [['this', 'is', 'the', 'first', 'document'], ['this', 'is', 'the', 'second', 'document']]
        >>> document_labels = ['document_one', 'document_two']
        >>> document_term_matrix = preprocessing.create_document_term_matrix(tokenized_corpus, document_labels)
        >>> vocabulary = document_term_matrix.columns
        >>> model = lda.LDA(n_topics=2, n_iter=1)
        >>> model = model.fit(document_term_matrix.as_matrix().astype(int))
        >>> topics = _show_lda_topics(model, vocabulary, num_keys=5)
        >>> index = [' '.join(keys[:3]) for keys in topics.values]
        >>> isinstance(_show_lda_document_topics(model, document_labels, index), pd.DataFrame)
        True
    """
    return pd.DataFrame(model.doc_topic_, index=document_labels, columns=index).T
    

def _show_lda_topics(model, vocabulary, num_keys):
    """Converts lda output to a DataFrame
    
    Description:
        With this function you can convert lda output to a DataFrame, 
        a more convenient datastructure.
        
    Note:

    Args:
        model: LDA model.
        vocab (list[str]): List of strings containing corpus vocabulary. 
        num_keys (int): Number of top keywords for topic
        
    Returns:
        DataFrame

    Example:
        >>> import lda
        >>> from dariah_topics import preprocessing
        >>> tokenized_corpus = [['this', 'is', 'the', 'first', 'document'], ['this', 'is', 'the', 'second', 'document']]
        >>> document_labels = ['document_one', 'document_two']
        >>> document_term_matrix = preprocessing.create_document_term_matrix(tokenized_corpus, document_labels)
        >>> vocabulary = document_term_matrix.columns
        >>> model = lda.LDA(n_topics=2, n_iter=1)
        >>> model = model.fit(document_term_matrix.as_matrix().astype(int))
        >>> isinstance(_show_lda_topics(model, vocabulary, num_keys=5), pd.DataFrame)
        True
    """
    log.info("Accessing topics from lda model ...")
    topics = []
    topic_word = model.topic_word_
    for i, topic_distribution in enumerate(topic_word):
        topics.append(np.array(vocabulary)[np.argsort(topic_distribution)][:-num_keys-1:-1])
    index = ['Topic {}'.format(n) for n in range(len(topics))]
    columns = ['Key {}'.format(n) for n in range(num_keys)]
    return pd.DataFrame(topics, index=index, columns=columns)


def _show_mallet_document_topics(doc_topics_file, index, easy_file_format):
    """Shows document-topic-mapping.
    Args:
        outfolder (str): Folder for MALLET output.
        doc_topics (str): Name of MALLET's doc_topic file. Defaults to 'doc_topics.txt'.
        topic_keys (str): Name of MALLET's topic_keys file. Defaults to 'topic_keys.txt'.

    ToDo: Prettify docnames
    
    Example:
        >>> import tempfile
        >>> index = ['first topic', 'second topic']
        >>> with tempfile.NamedTemporaryFile(suffix='.txt') as tmpfile:
        ...     tmpfile.write(b'0\\tdocument_one.txt\\t0.1\\t0.2\\n1\\tdocument_two.txt\\t0.4\\t0.5') and True
        ...     tmpfile.flush()
        ...     _show_mallet_document_topics(tmpfile.name, index, True) #doctest: +NORMALIZE_WHITESPACE
        True
                      document_one  document_two
        first topic            0.1           0.4
        second topic           0.2           0.5
    """
    document_topics_triples = []
    document_labels = []
    topics = []
    with open(doc_topics_file, 'r', encoding='utf-8') as file:
        for line in file:
            l = line.lstrip()
            if l.startswith('#'):
                lines = file.readlines()
                for line in lines:
                    documet_number, document_label, *values = line.rstrip().split('\t')
                    document_labels.append(os.path.splitext(os.path.basename(document_label))[0])
                    for topic, share in _grouper(2, values):
                        triple = (document_label, int(topic), float(share))
                        topics.append(int(topic))
                        document_topics_triples.append(triple)
            else:
                easy_file_format = True
                break
    if easy_file_format:
        document_topics = pd.read_table(doc_topics_file, sep='\t', header=None)
        document_topics.index = [os.path.splitext(os.path.basename(document_label))[0] for document_label in document_topics[1]]
        document_topics = document_topics.drop([0, 1], axis=1)
        document_topics.columns = index
        return document_topics.T
    else:
        document_topics_triples = sorted(document_topics_triples, key=operator.itemgetter(0, 1))
        document_labels = sorted(document_labels)
        num_documents = len(document_labels)
        num_topics = len(topics)
        document_topics = np.zeros((num_documents, num_topics))
        for triple in document_topics_triples:
            document_label, topic, share = triple
            index_num = document_labels.index(document_label)
            document_topics[index_num, topic] = share
    return pd.DataFrame(document_topics, index=index, columns=columns.T)


def _show_mallet_topics(path_to_topic_keys_file):
    """Show topic-key-mapping.

    Args:
        outfolder (str): Folder for Mallet output,
        topicsKeyFile (str): Name of Mallets' topic_key file, default "topic_keys"

    #topic-model-mallet
    Note: FBased on DARIAH-Tutorial -> https://de.dariah.eu/tatom/topic_model_mallet.html

    ToDo: Prettify index
    
    Example:    
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(suffix='.txt') as tmpfile:
        ...     tmpfile.write(b'0\\t0.5\\tthis is the first document\\n1\\t0.5\\tthis is the second document') and True
        ...     tmpfile.flush()
        ...     _show_mallet_topics(tmpfile.name)
        True
                Key 0 Key 1 Key 2   Key 3     Key 4
        Topic 0  this    is   the   first  document
        Topic 1  this    is   the  second  document
    """
    log.info("Accessing topics from MALLET model ...")
    topics = []
    with open(path_to_topic_keys_file, 'r', encoding='utf-8') as file:
        for line in file.readlines():
            _, _, keys = line.split('\t')
            keys = keys.rstrip().split(' ')
            topics.append(keys)
    index = ['Topic {}'.format(n) for n in range(len(topics))]
    columns = ['Key {}'.format(n) for n in range(len(topics[0]))]
    return pd.DataFrame(topics, index=index, columns=columns)


def _save_matrix_market(document_term_matrix, path):
    """
    Writes a `document_term_matrix` designed for large corpora to `Matrix Market <http://math.nist.gov/MatrixMarket/formats.html#MMformat>`_ file (`.mm`). Libraries like `scipy <https://www.scipy.org>`_
    and `gensim <https://radimrehurek.com/gensim/>`_ are able to read and process
    the Matrix Market format. This private function is wrapped in `save_document_term_matrix()`.
    
    **Use the function `preprocessing.create_document_term_matrix()` to create a
    document-term matrix.**

    Args:
        document_term_matrix (pandas.DataFrame): Document-term matrix with only
            one column corresponding to type frequencies and a pandas MultiIndex
            with `document_ids` for level 0 and `type_ids` for level 1. Will be
            saved as `document_term_matrix.mm`.
        path (str): Path to the output directory.

    Returns:
        None.

    Example:
    """
    num_docs = document_term_matrix.index.get_level_values('document_id').max()
    num_types = document_term_matrix.index.get_level_values('type_id').max()
    sum_counts = document_term_matrix[0].sum()
    header = "{} {} {}\n".format(num_docs, num_types, sum_counts)

    with open(os.path.join(path, 'document_term_matrix.mm'), 'w', encoding='utf-8') as file:
        file.write("%%MatrixMarket matrix coordinate real general\n")
        file.write(header)
        document_term_matrix.to_csv(file, sep=' ', header=None)
    return None

def show_topic_key_weights(topic_no, num_keys, model=None, vocabulary=None, topic_word_weights_file=None, sort_ascending=None):
    if vocabulary is not None and topic_word_weights_file is None:
        key_weights = _show_lda_key_weights(model, vocabulary, topic_no, num_keys)
    elif vocabulary is None and topic_word_weights_file is None:
        key_weights = _show_gensim_key_weights(model, topic_no, num_keys)
    elif topic_word_weights_file is not None:
        key_weights = _show_mallet_key_weights(topic_word_weights_file, topic_no)
    if sort_ascending is None:
        return pd.Series(key_weights)[:num_keys]
    else:
        return pd.Series(key_weights).sort_values(ascending=sort_ascending)[:num_keys]

def _show_lda_key_weights(model, vocabulary, topic_no, num_keys):
    return {key: weight for key, weight in zip(vocabulary[:num_keys], model.components_[topic_no][:num_keys])}

def _show_gensim_key_weights(model, topic_no, num_keys):
    return dict(model.show_topic(topic_no, num_keys))

def _show_mallet_key_weights(topic_word_weights_file, topic_no):
    key_weights = pd.read_table(topic_word_weights_file, sep='\t', header=None, names=['topic_id', 'key', 'weight'])
    key_weights = key_weights[key_weights['topic_id'] == topic_no].drop('topic_id', axis=1)
    return key_weights.set_index('key')['weight'].to_dict()
    
def get_sorted_values_from_distribution(values, distribution, length):
    return np.array(values)[np.argsort(distribution)][:-length-1:-1]
