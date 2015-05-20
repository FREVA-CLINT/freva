import re

class Esgf2SolrConfig(object):
    def cmip5(self,dataset):
        filename        = dataset['title']
        cmip5_structure = dict(
        filename        = filename,
        project         = dataset['project'][0],
        product         = dataset['product'][0],
        institute       = dataset['institute'][0],
        model           = re.sub(r"\)","",re.sub(r"[\.\(\,]","-",dataset['model'][0])),
        experiment      = dataset['experiment'][0],
        time_frequency  = dataset['time_frequency'][0],
        realm           = dataset['realm'][0],
        cmor_var        = [i for i in dataset['variable'] if i+'_' in filename][0],
        ensemble        = dataset['ensemble'][0])
        
        return cmip5_structure
    
    def specs(self,dataset):
        filename        = dataset['title']
        year            = str(int(re.compile(r'_S(?P<year>\d{4})\d{2}\d{2}_'+\
                                  dataset['ensemble'][0]).search(filename).group('year'))+0)
        
        specs_structure = dict(
        filename       = re.sub(dataset['experiment'][0]+'_S\d{8}_'+dataset['ensemble'][0],\
                                dataset['experiment'][0]+year+'_'+dataset['ensemble'][0],filename),
        project        = dataset['project'][0],
        product        = dataset['product'][0],
        institute      = dataset['institute'][0],
        model          = re.sub(r"\)","",re.sub(r"[\.\(\,]","-",dataset['model'][0])),
        experiment     = dataset['experiment'][0]+year,
        time_frequency = dataset['time_frequency'][0],
        realm          = dataset['realm'][0],
        cmor_var       = [i for i in dataset['variable'] if i+'_' in filename][0],
        ensemble       = dataset['ensemble'][0])
        
        return specs_structure
    
    def project_select(self,dataset):
        options = {'CMIP5' : self.cmip5,
                   'specs' : self.specs,
                   }
        return options[dataset['project'][0]](dataset)
    
class Solr2EsgfConfig(object):
    def cmip5(self):
        return
    def specs(self):
        return
    