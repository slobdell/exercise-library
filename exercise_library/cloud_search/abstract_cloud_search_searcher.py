from abc import ABCMeta

from .amazon_client import AmazonClient


class AbstractCloudSearchSearcher(AmazonClient):

    __metaclass__ = ABCMeta

    DEFAULT_PARSER = "structured"
    DEFAULT_PAGE_SIZE = 500

    def __init__(self, domain_index):
        self.domain = self.get_domain(domain_index)
        self.search_connection = self.domain.get_search_service()

    def execute_query_string_values_list(self, query_string, field_name):
        amazon_query = self.search_connection.build_query(q=query_string,
                                                          size=self.DEFAULT_PAGE_SIZE,
                                                          return_fields=[field_name],
                                                          parser=self.DEFAULT_PARSER)
        json_search_results = [json_blob for json_blob in self.search_connection.get_all_hits(amazon_query)]
        return [json_blob['fields'][field_name] for json_blob in json_search_results]

    def execute_query_string(self, query_string):
        amazon_query = self.search_connection.build_query(q=query_string,
                                                          size=self.DEFAULT_PAGE_SIZE,
                                                          parser=self.DEFAULT_PARSER)
        json_search_results = [json_blob for json_blob in self.search_connection.get_all_hits(amazon_query)]
        return [json_blob['fields'] for json_blob in json_search_results]

    def execute_query_facet_search(self, query_string, facet_field_names):
        facet_dict = {facet_field: "{}" for facet_field in facet_field_names}
        amazon_query = self.search_connection.build_query(q=query_string,
                                                          size=0,
                                                          facet=facet_dict,
                                                          parser=self.DEFAULT_PARSER)
        search_result = self.search_connection(amazon_query)
        return search_result.facets

    def execute_paged_query_string(self, query_string, page_index, page_size):
        # NOTE: Amazon Cloud Search does not support start > 10,000.  Docs say
        # to use a cursor for that case, did not build out since case not yet
        # reached
        amazon_query = self.search_connection.build_query(q=query_string,
                                                          size=page_size,
                                                          start=page_index,
                                                          parser=self.DEFAULT_PARSER)
        search_result = self.search_connection(amazon_query)
        all_hits = [doc for doc in search_result]
        json_search_results = [json_blob for json_blob in all_hits]
        return [json_blob['fields'] for json_blob in json_search_results]

    def execute_query_string_count(self, query_string):
        amazon_query = self.search_connection.build_query(q=query_string,
                                                          parser=self.DEFAULT_PARSER)
        return self.search_connection.get_num_hits(amazon_query)
