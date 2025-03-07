"""Retrieve annotated data from BigQuery."""
from google.cloud import bigquery

from linalgo.annotate.models import Annotation, Document


class BQClient:

    def __init__(self, task_id):
        self.client = bigquery.Client()
        self.task_id = task_id

    def _get_query_data(self, query):
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "task_id", "STRING", self.task_id),
            ]
        )
        job = self.client.query(query, job_config=job_config)
        return job.result()

    def get_annotations(self):
        prefix = "linalgo-infra.linhub_prod.public_"
        query = (
            'SELECT la.* '
            f'FROM `{prefix}linhub_corpus` lc '
            f'JOIN `{prefix}linhub_task_corpora` ltc ON ltc.corpus_id = lc.id '
            f'LEFT JOIN `{prefix}linhub_annotation` la ON la.task_id = ltc.task_id '
            'WHERE ltc.task_id = @task_id;'
        )
        rows = self._get_query_data(query)
        return [Annotation.from_bq_row(row) for row in rows]

    def get_documents(self):
        prefix = "linalgo-infra.linhub_prod.public_"
        query = (
            'SELECT ld.* '
            f'FROM `{prefix}linhub_document` ld '
            f'JOIN `{prefix}linhub_corpus` lc on lc.id = ld.corpus_id '
            f'JOIN `{prefix}linhub_task_corpora` ltc ON ltc.corpus_id = lc.id '
            'WHERE ltc.task_id = @task_id;'
        )
        rows = self._get_query_data(query)
        return [Document.from_bq_row(row) for row in rows]


__all__ = ['BQClient']
