"""
Created on 17.05.2016

@author: Sebatian Illing
"""

import pytest
import os


def test_struct():
    from evaluation_system.misc.utils import Struct

    ref_dict = {"a": 1, "b": 2}
    s = Struct(**ref_dict)
    assert "a" in s.__dict__
    assert s.validate(1)
    assert s.a == 1
    assert "b" in s.__dict__
    assert s.b == 2
    assert s.validate(2)
    assert s.toDict() == ref_dict
    assert Struct.from_dict(ref_dict) == s
    assert s.__repr__() == "<a:1,b:2>"

    # recursion
    ref_dict = {"a": {"b": {"c": 1}}}
    s = Struct.from_dict(ref_dict, recurse=True)
    assert "a" in s.__dict__
    assert "b" in s.a.__dict__
    assert "c" in s.a.b.__dict__
    assert s.a.b.validate(1)
    assert s.a.b.c == 1
    assert s.__repr__() == "<a:<b:<c:1>>>"


def test_template_dict():
    from evaluation_system.misc.utils import TemplateDict

    t = TemplateDict(a=1, b=2, c="$a")
    res = t.substitute(dict(x="$b$b$b", y="$z", z="$a"), recursive=False)
    assert res == {"x": "222", "y": "$z", "z": "1"}
    res = t.substitute(dict(x="$b$b$b", y="$c", z="$a"), recursive=True)
    assert res == {"x": "222", "y": "1", "z": "1"}
    tmp = {}
    # the maximal amount depends on de order they get resolved, and in
    # dictionaries this order is not
    # even given by anything in particular (e.g. alphabetic).
    # for a transitive substitution (a=b,b=c,c=d,...) the best case is
    # always 1 and the worst is ceil(log_2(n))
    # We have a maximal_iterations of 15 so we can substitute *at
    # least* 2^15=32768 variables
    max_it = 5000
    for l in range(max_it):
        tmp["a_%s" % l] = "$a_%s" % (l + 1)
    tmp["a_%s" % max_it] = "end"
    res = t.substitute(tmp, recursive=True)
    assert all([r == "end" for r in res.values()])
    # check recursions that doesn't work
    tmp["a_%s" % max_it] = "$a_0"
    with pytest.raises(Exception):
        t.substitute(tmp, recursive=True)
    with pytest.raises(Exception):
        t.substitute(dict(x="$y", y="$x"), recursive=True)
    with pytest.raises(Exception):
        t.substitute(dict(x="$y", y="$z", z="$x"), recursive=True)


def test_metadict_creation():
    from evaluation_system.misc.utils import metadict

    m1 = metadict(dict(a=1, b=2, c=[1, 2, 3]))
    m2 = metadict(a=1, b=2, c=[1, 2, 3])
    assert m1 == m2
    m3 = metadict(a=1, b=2, c=[1, 2, 3])
    m3.setMetadata("a", test=1)
    # metadata is just a parallel storage and should not affect the data.
    assert m1 == m3
    # the  'compact_creation' is a special key!
    m4 = metadict(compact_creation=False, a=1, b=2, c=[1, 2, 3])
    assert m1 == m4
    assert not ("compact_creation" in m4)
    # but after creation you should be able to use it
    m4["compact_creation"] = True
    assert not (m1 == m4)
    assert "compact_creation" in m4
    # setting compact creation to True should only affect tuples! Not lists.
    m5 = metadict(compact_creation=True, a=1, b=2, c=[1, 2, 3])
    assert m1 == m5
    # Should fail if compact_creation is set and values are bad formed (
    # i.e. iff tuple then (value, dict)
    with pytest.raises(AttributeError):
        metadict(compact_creation=True, a=(1, 2), b=2, c=[1, 2, 3])
    with pytest.raises(AttributeError):
        metadict(compact_creation=True, a=(1, [2, 3]), b=2, c=[1, 2, 3])
    # Compact creation should produce the same outcome as the normal one
    m6 = metadict(compact_creation=True, a=(1, dict(test=1)), b=2, c=[1, 2, 3])
    assert m1 == m6
    assert m3.getMetadata("a") == m6.getMetadata("a")


def test_metadict_copy():
    from evaluation_system.misc.utils import metadict

    m = metadict(dict(a=1, b=2, c=[1, 2, 3]))
    n = m.copy()
    n["c"][0] = 0
    # check we have a deepcopy of the items
    assert n["c"][0] != m["c"][0]


def test_printable_list():
    from evaluation_system.misc.utils import PrintableList

    a = [2, 3, 4, 5]
    p_list = PrintableList(a)
    assert p_list == a  # list creation
    assert str(p_list) == "2,3,4,5"  # string functionality
    p_list = PrintableList(a, seperator=":")
    assert str(p_list) == "2:3:4:5"  # string functionality


def test_super_make_dirs(temp_dir):
    from evaluation_system.misc.utils import supermakedirs

    path = temp_dir / "should" / "exist" / "now"
    res = supermakedirs(str(path), 0o777)
    assert path.is_dir
    assert os.access(path, os.W_OK)
    assert os.access(path, os.R_OK)


def test_mp_wrap_fn():
    def test_f(x, y):
        return x * y

    from evaluation_system.misc.utils import mp_wrap_fn

    res = mp_wrap_fn([test_f, 3, 2])
    assert res == 6
