import os
import shutil

import pytest

from evaluation_system.tests import run_command_with_capture, similar_string

def test_index_len(dummy_solr):
    assert dummy_solr.all_files.status()['index']['numDocs'] == 5
    assert dummy_solr.latest.status()['index']['numDocs'] == 3

def test_freva_databrowser_method(dummy_solr):
    from freva import databrowser
    all_files_output = sorted([f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc',
                               f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
                               f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc'])
    res = list(databrowser(variable='ua'))
    assert res == [f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc']
    target = sorted([f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
                      f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc'])
    res = sorted(databrowser(variable=['ua', 'tauu']))
    assert res == target
    res = sorted(databrowser(variable=['ua', 'tauu', 'wetso2']))
    assert res == all_files_output
    v = 'v20110419'
    res = sorted(databrowser(variable='ua', version=v))
    assert v in res[0]
    with pytest.raises(TypeError):
        databrowser('badoption')
    res = databrowser(all_facets=True)
    assert isinstance(res, dict)
    target = sorted(['cmor_table', 'product', 'realm', 'data_type', 'institute',
              'project', 'time_frequency', 'experiment', 'variable', 'model',
               'ensemble'])
    res = sorted(databrowser(attributes=True))
    assert sorted(target) == res

def test_search_files_cmd(dummy_solr, stdout):
     from evaluation_system.commands.basecommand import CommandError

     all_files_output = sorted([f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/historical/mon/aerosol/aero/r2i1p1/v20110728/wetso2/wetso2_aero_HadCM3_historical_r2i1p1_190912-193411.nc',
             f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
             f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc'])
     from evaluation_system.commands.databrowser import Command
     cmd = Command()
     res = sorted([f for f in run_command_with_capture(cmd, stdout, []).split('\n') if f])
     assert len(res) == len(all_files_output)
     assert res == all_files_output
     #assert similar_string('\n'.join(res), all_files_output, 0.95) is True
     res = run_command_with_capture(cmd, stdout, ['variable=ua'])
     assert res == f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc\n'
     res = run_command_with_capture(cmd, stdout, ['variable=ua', 'variable=tauu'])
     target = sorted([f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2009/mon/atmos/Amon/r7i2p1/v20110819/ua/ua_Amon_HadCM3_decadal2009_r7i2p1_200911-201912.nc',
             f'{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc'])
     res =  [f for f in sorted(res.split('\n')) if f]
     assert res == target
     res = run_command_with_capture(cmd, stdout, ['variable=ua', 'variable=tauu', 'variable=wetso2'])
     res =  [f for f in sorted(res.split('\n')) if f]
     assert res == all_files_output
     # search specific version
     v = 'v20110419'
     res = run_command_with_capture(cmd, stdout, ['variable=ua', 'version=%s' % v])
     assert v in res
     # test bad input
     with pytest.raises(SystemExit):
         with pytest.raises(CommandError):
             cmd.run(['badoption'])()

def test_search_facets(dummy_solr, stdout):
     from evaluation_system.commands.databrowser import Command
     from freva import databrowser
     cmd = Command()
     all_facets = [map(str.strip, f.split(':')) for f in """cmor_table: aero,amon
product: output1
realm: aerosol,atmos
data_type: cmip5
institute: mohc
project: cmip5
time_frequency: mon
experiment: decadal2008,decadal2009,historical
variable: tauu,ua,wetso2
model: hadcm3
ensemble: r2i1p1,r7i2p1,r9i3p1
""".split('\n') if f]
     res =  run_command_with_capture(cmd, stdout, ['--all-facets'])
     res = [map(str.strip, f.split(':')) for f in res.split('\n') if f]
     assert dict(res) == dict(all_facets)
     all_facets = {'product': ['output1'],
                   'realm': ['aerosol', 'atmos'],
                   'data_type': ['cmip5'],
                   'institute': ['mohc'],
                   'project' : ['cmip5'],
                   'time_frequency': ['mon'],
                   'experiment': ['decadal2008', 'decadal2009', 'historical'],
                   'variable': ['tauu', 'ua', 'wetso2'],
                   'model': ['hadcm3'],
                   'ensemble': ['r2i1p1','r7i2p1', 'r9i3p1']}
     res = run_command_with_capture(cmd, stdout, ['--facet=variable'])
     assert res == 'variable: tauu,ua,wetso2\n'
     res = run_command_with_capture(cmd, stdout, ['--facet=variable', 'experiment=historical'])
     assert res == 'variable: wetso2\n'
     res = run_command_with_capture(cmd, stdout, ['--facet=variable', 'facet.limit=2'])
     assert res == 'variable: tauu,ua...\n'
     res = run_command_with_capture(cmd, stdout, ['--facet=variable', '--count-facet-values'])
     assert res == 'variable: tauu (1),ua (1),wetso2 (1)\n'

def test_show_attributes(dummy_solr, stdout):

    from evaluation_system.commands.databrowser import Command
    cmd = Command()
    res = run_command_with_capture(cmd, stdout, ['--attributes']).strip().split(',')
    res = sorted([f.strip() for f in res if f])
    target = sorted(['cmor_table', 'product', 'realm', 'data_type', 'institute',
              'project', 'time_frequency', 'experiment', 'variable', 'model',
               'ensemble'])
    assert target == res

def test_solr_backwards(dummy_solr, stdout):
    
    from evaluation_system.commands.databrowser import Command
    cmd = Command()
    res = run_command_with_capture(cmd, stdout, ['--all-facets', f'file="\{dummy_solr.tmpdir}/cmip5/output1/MOHC/HadCM3/decadal2008/mon/atmos/Amon/r9i3p1/v20120523/tauu/\\tauu_Amon_HadCM3_decadal2008_r9i3p1_200811-201812.nc"'])
    res = [map(str.strip, f.split(':')) for f in res.split('\n') if f]
    target =  [map(str.strip, f.split(':')) for f in """cmor_table: amon
product: output1
realm: atmos
data_type: cmip5
institute: mohc
project: cmip5
time_frequency: mon
experiment: decadal2008
variable: tauu
model: hadcm3
ensemble: r9i3p1
""".split('\n') if f]
    assert dict(res) == dict(target)
