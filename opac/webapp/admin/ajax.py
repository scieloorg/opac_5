# coding: utf-8
from flask_admin._compat import as_unicode
from flask_admin.contrib.sqla.ajax import QueryAjaxModelLoader
from flask_admin.model.ajax import AjaxModelLoader


class CustomQueryAjaxModelLoader(AjaxModelLoader):
    def __init__(self, name, model, **options):
        """
        Constructor.
        :param fields:
            Fields to run query against
        """
    
        super(CustomQueryAjaxModelLoader, self).__init__(name, model, **options)
        self.model = model

    def format(self, model):
        # mudança minima porém necessária, o atributo id no modelo é _id
        if not model:
            return None
        return (as_unicode(model._id), as_unicode(model))

    def get_one(self, pk):
        # mudança minima porém necessária, o atributo id no modelo é _id
        return self.model.objects.filter(_id=pk).first()
