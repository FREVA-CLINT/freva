"""
Created on 30.05.2016

@author: Sebastian Illing
"""

from evaluation_system.tests import run_command_with_capture


def test_show_facet(esgf_command, stdout, dummy_config):
    res = run_command_with_capture(
            esgf_command,
            stdout,
            ['--show-facet=project,product'])
    assert '[product]' in res
    assert '[project]' in res

def test_find_files(esgf_command, stdout, search_dict, dummy_config):


    result_to_be = ['http://esgf1.dkrz.de/thredds/fileServer/cmip5/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/v20120529/tas/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
                    'http://aims3.llnl.gov/thredds/fileServer/cmip5_css02_data/cmip5/output1/MPI-M/MPI-ESM-LR/decadal2000/mon/atmos/Amon/r1i1p1/tas/1/tas_Amon_MPI-ESM-LR_decadal2000_r1i1p1_200101-201012.nc',
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
