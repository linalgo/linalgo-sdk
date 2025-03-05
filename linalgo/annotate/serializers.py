from .bbox import BoundingBox
from linalgo.annotate import models


class Serializer:

    def __init__(self, instance):
        self.instance = instance
        self.many = hasattr(instance, '__len__')

    def serialize(self):
        if self.many:
            return [self._serialize(i) for i in self.instance]
        return self._serialize(self.instance)


class BoundingBoxSerializer(Serializer):

    @staticmethod
    def _serialize(instance):
        s = {
            'vertex': instance.vertex,
            'height': instance.height,
            'width': instance.width
        }
        return s

class XPathSelectorSerializer(Serializer):

    @staticmethod
    def _serialize(instance):
        s = {
            'startContainer': instance.start_container,
            'endContainer': instance.end_container,
            'startOffset': instance.start_offset,
            'endOffset': instance.end_offset
        }
        return s

class SelectorSerializerFactory:

    @staticmethod
    def create(instance):
        if type(instance) == BoundingBox:
            return BoundingBoxSerializer(instance)
        elif isinstance(instance, models.XPathSelector):
            return XPathSelectorSerializer(instance)
        else:
            raise Exception(f"No serializer factory for {type(instance)}")


class TargetSerializer(Serializer):

    @staticmethod
    def _serialize(target):
        s = {
            'source': target.source.id,
            'selector': []
        }
        for selector in target.selector:
            serializer = SelectorSerializerFactory.create(selector)
            s['selector'].append(serializer.serialize())
        return s


class AnnotationSerializer(Serializer):

    @staticmethod
    def _serialize(instance):
        annotator_id = None
        if instance.annotator is not None:
            annotator_id = instance.annotator.id
        target = None
        if instance.target is not None:
            target_serializer = TargetSerializer(instance.target)
            target = target_serializer.serialize()
        s = {
            'id': instance.id,
            'task_id': instance.task.id,
            'entity_id': instance.entity.id,
            'body': instance.body or '',
            'annotator_id': annotator_id,
            'document_id': instance.document.id,
            'created': instance.created.isoformat(),
            'target': target
        }
        return s

class DocumentSerializer(Serializer):
    @staticmethod
    def _serialize(instance):
        return {
            'id': instance.id,
            'uri': instance.uri,
            'content': instance.content,
            'corpus_id': instance.corpus.id
        }


class CorpusSerializer(Serializer):
    @staticmethod
    def _serialize(instance: models.Corpus):
        s = DocumentSerializer(instance.documents)
        return {
            'id': instance.id,
            'name': instance.name,
            'description': instance.description,
            'documents': s.serialize()
        }
