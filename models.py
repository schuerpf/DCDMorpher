import re

from django.contrib import admin
from django.db import connection, models

field_lookup = {
    'INTEGER': lambda **kwargs: models.IntegerField(**kwargs),
    'VARCHAR': lambda **kwargs: models.CharField(max_length=255, **kwargs),
    'FOREIGN': lambda model_name, **kwargs: models.ForeignKey(model_name, **kwargs),
}
    
class Morph(object):
    
    @classmethod
    def initialize_models(cls):
        
        class Meta:
            pass
        
        model_list = []
        cursor = connection.cursor()
        cursor.execute('select * from sqlite_master');
        for row in cursor.fetchall():
            if row[0] == u'table':
                model_list.append((row[1], row[4]))
        
        # fetch entity table
        entity_list = []
        cursor.execute('select * from Z_PRIMARYKEY')
        for row in cursor.fetchall():
            entity_list.append([row[0], row[1], 'Z' + row[1].upper()])
        
        for model_info in model_list:
            model_name = str(model_info[0])
            for entity in entity_list:
                if entity[2] == model_name:
                    model_name = str(entity[1])
            
            setattr(Meta, 'app_label', 'morph')
            setattr(Meta, 'db_table', str(model_info[0]))
            attrs = {'__module__': '', 'Meta': Meta}
            
            # constructing model fields
            m = re.search(r'\( ([\w\s,]+) \)', model_info[1])
            if not m:
                continue
            definition_string = m.group(1)
            
            if definition_string:
                fields = [field.split() for field in definition_string.split(',')]
                first = True
                for field in fields:
                    kwargs = {'db_column':field[0]}
                    field_name = field[0]
                    verbose_name = field_name[1:].lower()
                    if first:
                        kwargs.update({'primary_key': True})
                        first = False
                    relation_matcher = re.search(r'Z(\d{1})[\w\d]+', field_name)
                    if relation_matcher:
                        entity_id = int(relation_matcher.groups(1)[0])
                        entity_model = None
                        for entity in entity_list:
                            if entity_id == entity[0]:
                                entity_model = 'morph.' + str(entity[1])
                                field_name = str(entity[1]).lower()
                        if entity_model:
                            kwargs.update({'to_field':'Z_PK'})
                            print (entity_model,field[0])
                            attrs.update({
                                      field_name: field_lookup['FOREIGN'](model_name=entity_model,**kwargs),
                            })
                    else:
                        kwargs.update({'verbose_name': verbose_name})
                        attrs.update({
                                      field_name: field_lookup[field[1]](**kwargs),
                        })
                new_model = type(model_name, (models.Model,), attrs)
                class Admin(admin.ModelAdmin):
                    pass
                admin.site.register(new_model)
        return