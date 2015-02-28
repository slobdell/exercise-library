from .amazon_client import AmazonClient
DEFAULT_BATCH_SIZE = 500


class CloudSearchIndexer(AmazonClient):

    def __init__(self, domain_index, batch_size=DEFAULT_BATCH_SIZE):
        self.domain = self.get_domain(domain_index)
        self.document_service_connection = self.domain.get_document_service()
        self.batch_size = batch_size
        self.items_in_batch = 0

    @classmethod
    def for_domain_index(cls, domain_index):
        return cls(domain_index)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        if len(args) > 1 and isinstance(args[1], Exception):
            raise args[1]
        self._commit_to_amazon()

    def _commit_to_amazon(self):
        self.document_service_connection.commit()
        self.document_service_connection.clear_sdf()
        self.items_in_batch = 0

    def add_document(self, cloud_search_document):
        cloud_search_json = cloud_search_document.to_cloud_search_json()
        cloud_search_json = self._nullify_falsy_values(cloud_search_json)
        self.document_service_connection.add(
            cloud_search_document.cloud_search_id,
            cloud_search_json
        )
        self._update_batch()

    def _nullify_falsy_values(self, json_dict):
        # falsy values create problems for empty iterables or None
        return {k: v for k, v in json_dict.items() if v or v == 0}

    def delete_document(self, cloud_search_document):
        self.document_service_connection.delete(cloud_search_document.cloud_search_id)
        self._update_batch()

    def _update_batch(self):
        self.items_in_batch += 1
        if self.items_in_batch == self.batch_size:
            self._commit_to_amazon()
