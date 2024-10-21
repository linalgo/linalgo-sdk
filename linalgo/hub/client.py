import io
from enum import Enum

from contextlib import closing
import csv
import requests
import zipfile

from linalgo.annotate.models import Annotation, Annotator, Corpus, Document, \
    Entity, Task
from linalgo.annotate.serializers import AnnotationSerializer, DocumentSerializer


class AssignmentType(Enum):
    REVIEW = 'R'
    LABEL = 'A'


class AssignmentStatus(Enum):
    ASSIGNED = 'A'
    COMPLETED = 'C'


class LinalgoClient:

    endpoints = {
        'annotators': 'annotators',
        'annotations': 'annotations',
        'corpora': 'corpora',
        'documents': 'documents',
        'entities': 'entities',
        'task': 'tasks',
        'annotations-export': 'annotations/export',
        'documents-export': 'documents/export',
    }

    def __init__(self, token, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.access_token = token

    def get(self, url, query_params={}):
        headers = {'Authorization': f"Token {self.access_token}"}
        res = requests.get(url, headers=headers, params=query_params)
        if res.status_code == 401:
            raise Exception(f"Authentication failed. Please check your token.")
        if res.status_code == 404:
            raise Exception(f"{url} not found.")
        elif res.status_code != 200:
            raise Exception(f"Request returned status {res.status_code}, {res.content}")
        return res.json()

    def post(self, url, data):
        headers = {'Authorization': f"Token {self.access_token}"}
        res = requests.post(url, data=data, headers=headers)
        if res.status_code == 401:
            raise Exception(f"Authentication failed. Please check your token.")
        if res.status_code == 404:
            raise Exception(f"{url} not found.")
        elif res.status_code != 201:
            raise Exception(f"Request returned status {res.status_code}, {res.content}")
        return res

    def request_csv(self, url, query_params={}):
        headers = {'Authorization': f"Token {self.access_token}"}
        # stream the file
        with closing(requests.get(url, stream=True, 
            headers=headers, params=query_params)) as res:
            if res.status_code == 401:
                raise Exception(f"Authentication failed. Please check your token.")
            if res.status_code == 404:
                raise Exception(f"{url} not found.")
            elif res.status_code != 200:
                raise Exception(f"Request returned status {res.status_code}")
            root = zipfile.ZipFile(io.BytesIO(res.content))
            f = root.namelist()
            if len(f):
                d = csv.DictReader(io.TextIOWrapper(root.open(f[0]), 'utf-8'))
            else:
                d = []
            return d

    def get_corpora(self):
        res = self.get(self.endpoints['corpora'])
        corpora = []
        for js in res['results']:
            corpus_id = js['id']
            corpus = self.get_corpus(corpus_id)
            corpora.append(corpus)
        return corpora

    def get_corpus(self, corpus_id):
        url = f"{self.api_url}/{self.endpoints['corpora']}/{corpus_id}/"
        res = self.get(url)
        corpus = Corpus.from_dict(res)
        # corpus = Corpus(name=res['name'], description=res['description'])
        documents = self.get_corpus_documents(corpus_id)
        corpus.documents = documents
        return corpus

    def get_corpus_documents(self, corpus_id):
        url = f"{self.api_url}/documents/?page_size=1000&corpus={corpus_id}"
        res = self.get(url)
        documents = []
        for d in res['results']:
            document = Document.from_dict(d)
            documents.append(document)
        return documents

    def get_tasks(self, task_ids=[]):
        url = "tasks/"
        tasks = []
        res = self.get(url)
        if len(task_ids) == 0:
            for js in res['results']:
                task_ids.append(js['id'])
        for task_id in task_ids:
            task = self.get_task(task_id)
            tasks.extend(task)
        return tasks

    def get_task_documents(self, task_id):
        query_params = {
            'task_id': task_id,
            'output_format': 'zip',
            'only_documents': True
        }
        api_url = "{}/{}/".format(
            self.api_url, self.endpoints['documents-export'])
        records = self.request_csv(api_url, query_params)
        data = [Document.from_dict(row) for row in records]
        return data

    def get_task_annotations(self, task_id):
        query_params = {'task_id': task_id, 'output_format': 'zip'}
        api_url = "{}/{}/".format(
            self.api_url, self.endpoints['annotations-export'])
        records = self.request_csv(api_url, query_params)
        data = [Annotation.from_dict(row) for row in records]
        return data

    def get_task(self, task_id, verbose=False, lazy=False):
        task_url = "{}/{}/{}/".format(
            self.api_url, self.endpoints['task'], task_id)
        if verbose:
            print(f'Retrivieving task with id {task_id}...')
        task_json = self.get(task_url)
        task = Task.from_dict(task_json)
        if lazy:
            return task
        if verbose:
            print('Retrieving annotators...', end=' ')
        task.annotators = self.get_annotators(task)
        if verbose:
            print(f'({len(task.annotators)} found)')
        if verbose:
            print('Retrieving entities...', end=' ')
        params = {'tasks': task.id, 'page_size': 1000}
        if verbose:
            print(f'({len(task.entities)} found)')
        entities_url = "{}/{}".format(self.api_url, self.endpoints['entities'])
        entities_json = self.get(entities_url, params)
        task.entities = [Entity.from_dict(e) for e in entities_json['results']]
        if verbose:
            print('Retrieving documents...', end=' ')
        task.documents = self.get_task_documents(task_id)
        if verbose:
            print(f'({len(task.documents)} found)')
        if verbose:
            print('Retrieving annotations...', end=' ')
        task.annotations = self.get_task_annotations(task_id)
        if verbose:
            print(f'({len(task.annotations)} found)')
        return task

    def get_annotators(self, task):
        if isinstance(task, str):
            task = Task(unique_id=task)
        params = {'tasks': task.id, 'page_size': 1000}
        annotators_url = "{}/{}/".format(
            self.api_url, self.endpoints['annotators'])
        res = self.get(annotators_url, params)
        annotators = []
        for a in res['results']:
            annotator = Annotator.from_dict(a)
            annotators.append(annotator)
        return annotators

    def create_annotator(self, annotator):
        url = "{}/{}/".format(self.api_url, self.endpoints['annotators'])
        headers = { 'Authorization': f"Token {self.access_token}"}
        annotator_json = {
            'id': annotator.id,
            'name': annotator.name,
            'model': str(annotator.model),
            'owner': annotator.owner
        }
        res = requests.post(url, json=annotator_json, headers=headers)
        if res.status_code != 201:
            raise Exception(res.content)
        res = res.json()
        annotator.annotator_id = res['id']
        annotator.owner = res['owner']
        return annotator

    def create_annotations(self, annotations):
        url = "{}/{}/import_annotations/".format(self.api_url, self.endpoints['annotations'])
        headers = {'Authorization': f"Token {self.access_token}"}
        serializer = AnnotationSerializer(annotations)
        payload = serializer.serialize()
        res = requests.post(url, json=payload, headers=headers)
        return res
    
    def delete_annotations(self, annotations):
        url = "{}/{}/bulk_delete/".format(self.api_url, self.endpoints['annotations'])
        headers = {'Authorization': f"Token {self.access_token}"}
        annotations_ids = [annotation.id for annotation in annotations]
        res = requests.delete(url, json=annotations_ids, headers=headers)
        if res.status_code != 204:
            raise Exception(res.content)
        return res

    def assign(
            self, 
            document: Document, 
            annotator: Annotator, 
            task: Task, 
            reviewee=None,
            assignment_type=AssignmentType.LABEL.value
        ):
        doc_status = {
            'status': AssignmentStatus.ASSIGNED.value,
            'type': assignment_type,
            'document': document.id,
            'annotator': annotator.id,
            'task': task.id,
            'reviewee': reviewee
        }
        url = self.api_url + '/document-status/'
        res = self.post(url, doc_status)
        return res

    def unassign(self, status_id):
        headers = {'Authorization': f"Token {self.access_token}"}
        url = "{}/{}/{}/".format(self.api_url, '/document-status/', status_id)
        res = requests.delete(url, headers=headers)
        return res

    def get_schedule(self, task):
        query_params = {'task': task.id, 'page_size': 1000}
        docs = []
        next_url = "{}/{}/".format(self.api_url, '/document-status/')
        while next_url:
            res = self.get(next_url, query_params=query_params)
            next_url = res['next']
            docs.extend(res['results'])
        return docs
    
    def add_document(self, doc: Document, corpus: Corpus):
        url = f"{self.api_url}/corpora/{corpus.id}/add_document/"
        payload = DocumentSerializer(doc).serialize()
        return self.post(url, payload)
