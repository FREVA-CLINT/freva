"""
Created on 30.05.2016

@author: Sebastian Illing
"""

import json
import os
from evaluation_system.tests import run_command_with_capture


def test_show_facet(esgf_command, stdout, dummy_config):
    res = run_command_with_capture(
            esgf_command,
            stdout,
            ['--show-facet=project,product', '-d'])
    assert '[product]' in res
    assert '[project]' in res

def test_query(esgf_command, stdout, search_dict, dummy_config):
    res = run_command_with_capture(
            esgf_command,
            stdout,
            ['--debug', 'project=TEST', '--query=project,product', '--opendap'])
    res = json.loads(res)[0]
   
    assert 'project' in res.keys()
    res = run_command_with_capture(
            esgf_command,
            stdout,
            ['--debug', 'project=TEST','limit=1', '--query=project', '--gridftp'])
    
    assert "['TEST']" in res 
    res = run_command_with_capture(
            esgf_command,
            stdout,
            ['project=TEST', '--query=project', '--gridftp'])
    res = [r for r in res.split('\n') if r.strip()]
    num_res = len(res)
    res = run_command_with_capture(
            esgf_command,
            stdout,
            ['project=TEST','offset=1', '--query=project', '--gridftp'])
    res = [r for r in res.split('\n') if r.strip()]
    assert num_res == len(res) + 1

def test_freva_esgf_method(dummy_config):
    from freva import esgf
	
    result_to_be = ['http://esgf-data1.ceda.ac.uk/thredds/fileServer/esg_dataroot/cmip5/output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18500101-18591231.nc',
                    'http://esgf.nci.org.au/thredds/fileServer/replica/CMIP5/output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18500101-18591231.nc',
                    'http://esgf1.dkrz.de/thredds/fileServer/cmip5/cmip5/output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18500101-18591231.nc',
                    'http://esgf-data1.ceda.ac.uk/thredds/fileServer/esg_dataroot/cmip5/output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18600101-18691231.nc',
                    'http://esgf.nci.org.au/thredds/fileServer/replica/CMIP5/output1/MPI-M/MPI-ESM-LR/historical/day/atmos/day/r1i1p1/v20111006/tas/tas_day_MPI-ESM-LR_historical_r1i1p1_18600101-18691231.nc'                    ]
    res = esgf(project='CMIP5',experiment='historical',variable='tas',institute='MPI-M',time_frequency='day')
    for f in result_to_be:
        assert f in res
    #for f in result_to_be:
    #    assert f in res             
    res =esgf(show_facets='product')
    res=res["product"]['MRE2reanalysis']
    assert res == 6
    script_file = '/tmp/file_script.sh'
    res=esgf(project='CMIP5',model='MPI-ESM-LR', experiment='decadal2001', variable='tas', distrib=False,download_script=script_file)
    
    assert os.path.isfile(script_file)
    assert res == f"Download script successfully saved to {script_file}"
    assert oct(os.stat(script_file).st_mode)[-3:] == '755'
    
def test_find_files(esgf_command, stdout, search_dict, dummy_config):

    
    result_to_be = ['http://aims3.llnl.gov/thredds/fileServer/cmip5_css02_data/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/tas/1/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                    'http://esgf-data1.ceda.ac.uk/thredds/fileServer/esg_dataroot/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                    'http://esgf.nci.org.au/thredds/fileServer/replica/CMIP5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                    'http://esgf1.dkrz.de/thredds/fileServer/cmip5/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc']
    res = run_command_with_capture(esgf_command, stdout,
            [f'{key}={val}' for key, val in search_dict.items()])
    for f in result_to_be:
        assert f in res

    res = run_command_with_capture(esgf_command, stdout,
        ['--datasets'] + [f'{key}={val}' for key, val in search_dict.items()]
    )
    assert 'cmip5.output1.MPI-M.MPI-ESM-LR.decadal2000.mon.atmos.Amon.r1i1p1 - version: 20120529' in res

def test_download_script(esgf_command, stdout, search_dict, tmp_dir, dummy_config):
    fn = tmp_dir / 'download_test_script.sh'
    res = run_command_with_capture(esgf_command, stdout,
        ['%s=%s' % (key, val) for key, val in search_dict.items()]\
                + [f'--download-script={fn}']
    )
    assert fn.is_file()
    assert  res == f"Download script successfully saved to {fn}\n"
    assert oct(os.stat(fn).st_mode)[-3:] == '755'

#def test_catalogue(esgf_command, stdout, search_dict, tmp_dir, dummy_config):

