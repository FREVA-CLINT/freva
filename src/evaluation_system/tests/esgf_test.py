"""
Created on 30.05.2016

@author: Sebastian Illing
"""

import json
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
    assert "['test']" == res.lower().strip()
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
    from Freva import esgf
	
    result_to_be = ['http://esgf-data1.ceda.ac.uk/thredds/fileServer/esg_dataroot/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2001/day/atmos/day/r10i1p1/v20111122/tas/tas_day_MPI-ESM-LR_decadal2001_r10i1p1_20020101-20111231.nc',
	             'http://esgf1.dkrz.de/thredds/fileServer/cmip5/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2001/day/atmos/day/r10i1p1/v20111122/tas/tas_day_MPI-ESM-LR_decadal2001_r10i1p1_20020101-20111231.nc',
	             'http://esgf-data1.ceda.ac.uk/thredds/fileServer/esg_dataroot/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2001/day/atmos/day/r1i1p1/v20111122/tas/tas_day_MPI-ESM-LR_decadal2001_r1i1p1_20020101-20111231.nc',
	             'http://esgf1.dkrz.de/thredds/fileServer/cmip5/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2001/day/atmos/day/r1i1p1/v20111122/tas/tas_day_MPI-ESM-LR_decadal2001_r1i1p1_20020101-20111231.nc']
    res = esgf(project='cmip5',experiment='historical',variable='tas',institute='MPI-M',time_frequency='day')
    for f in result_to_be:
        assert f in res
    #for f in result_to_be:
    #    assert f in res             
    res =esgf(show_facets='product')
    assert res =={'product': {'MRE2reanalysis': 6, 'MRE3reanalysis': 54, 'MREreanalysis': 5, 'ORAreanalysis': 9, 'Regional Reanalysis': 10, 'baseline0': 5568, 'bias-adjusted-output': 1593, 'bioclimatic': 2, 'climate-projection': 423, 'downscaled': 10, 'elev': 1, 'forcing_dataset': 6602, 'historical': 54, 'input': 1111, 'input_secondary': 85, 'insitu': 104, 'model-output': 11678490, 'observations': 209, 'output': 765924, 'output1': 245232, 'output2': 3562, 'output_secondary': 116, 'reanalysis': 76, 'season-forecast': 20, 'vicoutput': 48, 'vicoutput-pconst': 36}}
    script_file = /tmp/ 'file_script.sh'
    res=esgf(project='CMIP5',model='MPI-ESM-LR', experiment='decadal2001', variable='tas', distrib=False,download_script=f'{script_file}')
    assert script_file.is_file()
    assert res == f"Download script successfully saved to {fn}\n"
    assert oct(script_file.stat().st_mode)[-3:] == '755'
    
def test_find_files(esgf_command, stdout, search_dict, dummy_config):

    
    result_to_be = ['http://esgf1.dkrz.de/thredds/fileServer/cmip5/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                    #'http://aims3.llnl.gov/thredds/fileServer/cmip5_css02_data/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/tas/1/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                    'http://esgf-data1.ceda.ac.uk/thredds/fileServer/esg_dataroot/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc']
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
    assert res == f"Download script successfully saved to {fn}\n"
    assert oct(fn.stat().st_mode)[-3:] == '755'

#def test_catalogue(esgf_command, stdout, search_dict, tmp_dir, dummy_config):

