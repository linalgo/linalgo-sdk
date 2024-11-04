import copy
from enum import Enum
from datetime import datetime
from typing import Dict, Iterable, List, Union
import json
import logging
import uuid

from linalgo.annotate.bbox import BoundingBox, Vertex


Selector = Union[BoundingBox]


class SelectorFactory:

    @staticmethod
    def factory(d: Dict):
        if type(d) == dict:
          if d == {}:
              return d
          if 'x' in d:
              v = Vertex(d['x'], d['y'])
              return BoundingBox.fromVertex(
                  v, height=d['height'], width=d['width'])
          elif 'startOffset' in d:
              return XPathSelector(
                  start_container=d['startContainer'],
                  end_container=d['endContainer'],
                  start_offset=d['startOffset'],
                  end_offset=d['endOffset']
            )
        elif type(d) == XPathSelector:
            return d
        raise Exception(f"No factory found for {type(d)}")


class XPathSelector:

    def __init__(self, start_container: str, end_container: str,
                 start_offset: int, end_offset: int):
        self.start_container = start_container
        self.end_container = end_container
        self.start_offset = start_offset
        self.end_offset = end_offset


class TargetFactory:

    @staticmethod
    def factory(data):
        if str(type(data)) == str(Target):
            return data
        elif type(data) == str:
            d = json.loads(data.replace("\'", "\""))
            return TargetFactory.from_dict(d)
        elif type(data) == dict:
            return TargetFactory.from_dict(data)
        raise NotImplementedError(f'No factory found for type {type(data)}')

    @staticmethod
    def from_dict(d: Dict):
        if d == {}:
            return Target(source=None, selector=[])
        return Target(
            source=Document.factory(d['source']),
            selector=[SelectorFactory.factory(s) for s in d['selector']]
        )


class Target(TargetFactory):

    def __init__(self, source: 'Document' = None,
                 selector: Iterable[Selector] = []):
        self.source = source
        self.selector = [SelectorFactory.factory(s) for s in selector]

    def copy(self):
        return Target(
            source=self.source,
            selector=[copy.deepcopy(s) for s in self.selector])


class RegistryMixin:

    def __new__(cls, *args, **kwargs):
        unique_id = kwargs.get('unique_id', str(uuid.uuid4()))
        unique_id = kwargs.get('id', unique_id)
        if not hasattr(cls, '_registry'):
            cls._registry = dict()
        if unique_id in cls._registry:
            return cls._registry[unique_id]
        else:
            obj = super().__new__(cls)
            obj.id = unique_id
            cls._registry[unique_id] = obj
            return obj

    def register(self):
        self._registry[self.id] = self

    def setattr(self, name, value):
        if not hasattr(self, name):
            self.__setattr__(name, value)
            return True
        attr = self.__getattribute__(name)
        if attr is None:
            self.__setattr__(name, value)
            return True
        elif value not in (None, [], set()):
            self.__setattr__(name, value)
            return True
        logging.info(f'Attribute {name} of {self} was not overridden')
        return False


class FromIdFactoryMixin:

    @classmethod
    def factory(cls, arg):
        if arg is None:
            return cls(unique_id='default')
        elif type(arg) == cls:
            return arg
        elif type(arg) == str:
            return cls(unique_id=arg)
        else:
            raise Exception(f'No factory method found for type {type(arg)}')


class AnnotationFactory:

    @staticmethod
    def from_dict(d: Dict):
        return Annotation(
            unique_id=d['id'],
            entity=Entity(unique_id=d['entity']),
            body=d['body'],
            annotator=Annotator(unique_id=d['annotator']),
            document=Document(unique_id=d['document']),
            task=Task(unique_id=d['task']),
            target=Target.factory(d['target']),
            created=d['created']
        )


class Annotation(RegistryMixin, FromIdFactoryMixin, AnnotationFactory):
    """
    Annotation class compatible with the W3C annotation data model.
    """

    def __init__(
            self, entity: 'Entity'=None, document: 'Document'=None, 
            body: str = None, annotator: 'Annotator' = None, 
            task: 'Task' = None, created=None, target: Target = None, 
            score: float = None, auto_track=True, **kwargs
        ):
        if 'entity_id' in kwargs:
            entity = kwargs['entity_id']
        self.setattr('entity', Entity.factory(entity))
        self.setattr('score', score)
        self.setattr('body', body)
        if 'task_id' in kwargs:
            task = kwargs['task_id']
        self.setattr('task', Task.factory(task))
        if 'annotator_id' in kwargs:
            annotator = kwargs['annotator_id']
        self.setattr('annotator', Annotator.factory(annotator))
        if 'document_id' in kwargs:
            document = kwargs['document_id']
        self.setattr('document', Document.factory(document))
        if auto_track:
            self.document.annotations.add(self)
        self.setattr('target', TargetFactory.factory(target))
        if created is None:
            created = datetime.now()
        elif isinstance(created, str):
            created = datetime.fromisoformat(created)
        self.setattr('created', created)
        self.register()

    def __repr__(self):
        return f'Annotation::{self.entity.name or self.entity.id}'

    def copy(self):
        target = self.target.copy()
        return Annotation(unique_id=str(uuid.uuid4()), entity=self.entity,
                document=self.document, task=self.task, target=target,
                body=self.body, annotator=self.annotator,  score=self.score)


class AnnotatorFactory:

    @staticmethod
    def from_dict(d):
        return Annotator(
            unique_id=d['id'],
            name=d['name'],
            owner=d['owner']
        )


class Annotator(RegistryMixin, FromIdFactoryMixin, AnnotatorFactory):
    """
    The Annotator class can create, delete or modify Annotations.
    """

    def __init__(self, name: str = None, model=None, task: 'Task' = None,
                 entity_id=None, threshold: float = 0, owner=None, 
                 **kwargs):
        self.setattr('name', name)
        self.setattr('task', Task.factory(task))
        self.setattr('owner', owner)
        self.setattr('model', model or 'MACHINE')
        self.setattr('entity_id', entity_id)
        self.setattr('threshold', threshold)
        self.register()

    def __repr__(self):
        return f'Annotator::{self.name or self.id}'

    def assign_task(self, task):
        self.task = task

    def _get_annotation(self, document):
        score = self.model.decision_function([document.content])[0]
        if score >= self.threshold:
            label = self.entoty_id
        else:
            label = 1  # Viewed
        annotation = Annotation(
            entity_id=label,
            score=score,
            text=document.content,
            annotator=self.id,
            task_id=self.task.id,
            document_id=document.id
        )
        return annotation

    def annotate(self, document):
        annotation = self._get_annotation(document)
        if annotation is not None:
            self.task.annotations.append(annotation)
            document.annotations.add(annotation)
        return annotation


class CorpusFactory:

    @staticmethod
    def from_dict(d):
        return Corpus(
            unique_id=d['id'],
            name=d['name'],
            description=d['description'],
        )


class Corpus(RegistryMixin, FromIdFactoryMixin, CorpusFactory):

    def __init__(self, name: str = None, description: str = None,
                 documents: Iterable['Document'] = [], **kwargs):
        self.setattr('name', name)
        self.setattr('description', description)
        if len(documents) > 0:
            self.setattr('documents', [Document.factory(d) for d in documents])
        self.register()

    def __repr__(self):
        return f'Corpus::{self.name or self.id}'


class DocumentFactory:

    @staticmethod
    def from_dict(d):
        return Document(
            unique_id=d['id'],
            uri=d['uri'],
            content=d['content'],
            corpus=Corpus(d['corpus'])
        )


class Document(RegistryMixin, FromIdFactoryMixin, DocumentFactory):
    """
    Base class that holds the document on which to perform annotations.
    """

    def __init__(self, content: str = None, uri: str = None,
                 corpus: Corpus = None, **kwargs):
        self.setattr('uri', uri)
        self.setattr('content', content)
        self.setattr('corpus', Corpus.factory(corpus))
        self.setattr('annotations', set())
        self.register()

    @property
    def entities(self):
        return list(set(a.entity for a in self.annotations))

    def __repr__(self):
        return f'Document::{self.id}'


class EntityFactory:

    @staticmethod
    def from_dict(d: Dict):
        return Entity(
            unique_id=d['id'],
            name=d['title'],
            color=d['color']
        )


class Entity(RegistryMixin, FromIdFactoryMixin, EntityFactory):

    def __init__(self, name: str = None, color: str = None, **kwargs):
        self.setattr('name', name)
        self.setattr('color', color)
        self.register()

    def __repr__(self):
        return f'Entity::{self.name or self.id}'


class TaskFactory:
    @staticmethod
    def from_dict(d):
        return Task(
            unique_id=d['id'],
            name=d['name'],
            description=d['description'],
            entities=[Entity(e) for e in d['entities']],
            corpora=[Corpus.factory(c) for c in d['corpora']],
            annotators=[Annotator(a) for a in d['annotators']],
        )


class Task(RegistryMixin, FromIdFactoryMixin, TaskFactory):
    """
    The Task class contains all information about a task: entities, corpora, 
    annotations.
    """

    def __init__(
            self, name: str = None, description: str = None,
            entities: List[Entity] = [], corpora: List[Corpus] = [],
            annotators: List[Annotator] = [], documents: List[Document] = [],
            annotations: Iterable[Annotation] = [], **kwargs):
        self.setattr('name', name)
        self.setattr('description', description)
        self.setattr('entities', [Entity.factory(e) for e in entities])
        self.setattr('corpora', [Corpus.factory(c) for c in corpora])
        self.setattr('annotators', [Annotator.factory(a) for a in annotators])
        self.setattr('annotations', [Annotation.factory(a) for a in annotations])
        self.setattr('documents', [Document.factory(d) for d in documents])
        self.register()

    def __repr__(self):
        return f'Task::{str(self.id)}'

    def add_annotation(self, annotation: Annotation):
        self.annotations.add(annotation)

    def add_document(self, document: Document):
        self.documents.add(document)


class DocumentStatus(Enum):
    Assigned = 'A'
    Completed = 'C'


class ScheduleType(Enum):
    Review = 'R'
    Annotate = 'A'


class Schedule(RegistryMixin):

    def __init__(
        self, 
        status: str, 
        type: str, 
        priority: float, 
        timestamp: str | datetime, 
        document: Document, 
        annotator: Annotator, 
        task: Annotator, 
        reviewee: Annotator,
        **kwargs
    ):
        self.status = DocumentStatus(status)
        self.type = ScheduleType(type)
        self.priority = priority
        self.timestamp = timestamp
        self.document = Document(document)
        self.annotator = Annotator(annotator)
        self.task = Task(task)
        self.reviewee = Annotator(reviewee)
    
    def __repr__(self) -> str:
        return f'Schedule::{self.type}::{self.status}'