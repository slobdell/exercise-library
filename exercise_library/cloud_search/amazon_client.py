import boto
from django.conf import settings


class AmazonClient(object):
    REGION = settings.AWS_CLOUDSEARCH_REGION

    _cls_domain_cache = {}

    def get_domain(self, domain_index):
        try:
            return self._cls_domain_cache[domain_index]
        except KeyError:
            self._cls_domain_cache[domain_index] = boto.connect_cloudsearch2(
                region=self.REGION).lookup(domain_index)
            return self._cls_domain_cache[domain_index]
