from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty


class AbstractCloudSearchDocument(object):

    __metaclass__ = ABCMeta

    @abstractproperty
    def cloud_search_id(self):
        ''' A string that represents a unique identifier; should mimic the primary key of a model '''
        pass

    @abstractmethod
    def to_cloud_search_json(self):
        ''' A JSON representation of the document that should match up with the index schema in Amazon '''
        pass
