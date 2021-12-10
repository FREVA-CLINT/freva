"""
Created on 18.05.2016

@author: Sebastian Illing
"""
import pytest


def test_crawl_my_data(dummy_settings, capsys):
    from freva import crawl_my_data
    from evaluation_system.misc.exceptions import ValidationError

    crawl_my_data()
    captured = capsys.readouterr()
    assert "Status: crawling ..." in captured.out
    assert "ok" in captured.out
    with pytest.raises(NotImplementedError):
        crawl_my_data(dtype="something")
    with pytest.raises(ValidationError):
        crawl_my_data("/tmp/forbidden/folder")
