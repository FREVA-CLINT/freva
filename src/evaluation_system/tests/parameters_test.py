# coding=utf-8
"""
Created on 10.05.2016

@author: Sebastian Illing
"""

import pytest


def test_infer_type(dummy_env):
    from evaluation_system.api.parameters import (
        ParameterType,
        Integer,
        Float,
        Bool,
        String,
        ValidationError,
    )

    assert ParameterType.infer_type(1).__class__ == Integer
    assert ParameterType.infer_type(1.0).__class__ == Float
    assert ParameterType.infer_type("str").__class__ == String
    assert ParameterType.infer_type(True).__class__ == Bool
    assert ParameterType.infer_type(str).__class__ == String
    with pytest.raises(ValueError):
        assert ParameterType.infer_type(type(str))


def test_parameter_type(dummy_env):
    from evaluation_system.api.parameters import String, ValidationError

    with pytest.raises(ValidationError):
        String(name="foo", max_items=0)
    s_type = String(
        name="foo", default="foo;bar", mandatory=True, max_items=2, item_separator=";"
    )
    assert s_type.to_str("foo;bar") == "foo;bar"
    assert s_type.to_str(["foo", "bar"]) == "foo;bar"
    s_type.item_separator = None
    assert s_type.to_str(["foo", "bar"]) == '["foo", "bar"]'
    assert s_type.parse('["foo"]') == ["foo"]
    assert s_type.parse("foo") == ["foo"]
    assert s_type.__str__() == s_type.get_type() == "String"


def test_parsing(dummy_env):
    from evaluation_system.api.parameters import (
        String,
        Integer,
        Float,
        Bool,
        Range,
        SelectField,
        SolrField,
        InputDirectory,
        Unknown,
        ValidationError,
    )

    test_cases = [
        (String(), [("asd", "asd"), (None, "None"), (1, "1"), (True, "True")], []),
        (
            String(regex="^x.*$"),
            [("xasd", "xasd")],
            ["aaaa", "the x is not in, the right place"],
        ),
        (
            String(regex="x+", max_items=3),
            [("xasd", ["xasd"]), ("xas,sxd,somex", ["xas", "sxd", "somex"])],
            ["missing a letter", "ok x, also ok xx, but not ok"],
        ),
        (
            Integer(),
            [("123", 123), ("0", 0), ("-1", -1), (True, 1)],
            ["+-0", "not a number!!", None],
        ),
        (
            Integer(max_items=2, item_separator=","),
            [
                ("123", [123]),
                ("0,4", [0, 4]),
                ([0, 3.1516], [0, 3]),
                ([0.999], [0]),
                (123.8, [123]),
            ],
            ["+-0", "not a number!!", [1, 2, 3]],
        ),
        (
            Float(),
            [
                ("123", 123.0),
                ("0", 0.0),
                ("-1.3", -1.3),
                ("-1e+2", -100.0),
                ("+2E-2", 0.02),
                (False, 0.0),
                ("12.", 12.0),
                (".42", 0.42),
            ],
            ["+-0", "not a number!!", "123,321.2", None],
        ),
        (
            Bool(),
            [
                ("1", True),
                ("0", False),
                ("True", True),
                ("false", False),
                ("no", False),
                ("YES", True),
            ],
            ["maybe", "", None],
        ),
        (
            Range(),
            [
                ("1960:1970", list(range(1960, 1970 + 1))),
                ("1970,1971,1972", [1970, 1971, 1972]),
                ("1980:5:2000", list(range(1980, 2000 + 1, 5))),
                ("1970:1971-1970", [1971]),
                ("1950:10:1980,1985-1960:1970", [1950, 1980, 1985]),
            ],
            ["1:1:1:1", "", None, "ab:c", []],
        ),
        (
            SelectField(
                options={"option1": "value1", "another_option": "Some other value"}
            ),
            [("value1", "option1"), ("Some other value", "another_option")],
            [("bad value", "")],
        ),
        (SolrField(facet="variable"), [("tas", "tas"), ("pr", "pr")], []),
        (InputDirectory(), [("/home/user", "/home/user")], []),
        (Unknown(), [("test", "test")], []),
    ]
    for case_type, positive_cases, negative_cases in test_cases:
        for expected, result in positive_cases:
            parsed_value = case_type.parse(expected)
            if isinstance(parsed_value, list):
                assert type(parsed_value[0]) == case_type.base_type
            else:
                assert type(parsed_value) == case_type.base_type
            assert parsed_value == result
        for unparseable in negative_cases:
            try:
                with pytest.raises(TypeError):
                    case_type.parse(unparseable)
            except:
                try:
                    with pytest.raises(ValueError):
                        case_type.parse(unparseable)
                except:
                    with pytest.raises(ValidationError):
                        case_type.parse(unparseable)


def test_parameters_dictionary(dummy_env):
    from evaluation_system.api.parameters import (
        String,
        ParameterDictionary,
        ValidationError,
    )

    p1 = String(name="a_param1", default="default default 1")
    p2 = String(
        name="a_param2", default="default default 2", max_items=3, item_separator=":"
    )
    assert p2.parse("a:b:C") == ["a", "b", "C"]
    with pytest.raises(ValueError):
        ParameterDictionary(p1, p2, p2)
    p_dict = ParameterDictionary(p1, p2)
    assert "ParameterDictionary(" in p_dict.__str__()
    assert "a_param2<String>:" in p_dict.__str__()
    assert "a_param1<String>:" in p_dict.__str__()
    assert len(p_dict) == 3
    assert p1.name in p_dict and p_dict[p1.name] == p1.default
    assert p2.name in p_dict and p_dict[p2.name] == p2.default
    assert len(p_dict.parameters()) == 3
    with pytest.raises(ValidationError):
        p_dict.get_parameter("a_pram1")
    # TODO: Fix error
    # self.assertEquals(p_dict.get_parameter(p1.name), p1)
    # self.assertEquals(p_dict.get_parameter(p2.name), p2)

    # Check parameters remain in the order we put them
    params = [String(name="extra_scheduler_options", default="")]
    for i in range(1000):
        params.append(String(name=str(i), default=i))
    p_dict = ParameterDictionary(*params)
    assert sorted(p_dict.keys()) == sorted([p.name for p in params])
    assert list(p_dict.values()) == [p.default for p in params]
    assert p_dict.parameters() == params


def test_parse_arguments(dummy_env):
    from evaluation_system.api.parameters import (
        String,
        ParameterDictionary,
        Integer,
        Float,
        Bool,
        String,
        File,
        Date,
        Range,
        ValidationError,
    )

    p_dict = ParameterDictionary(String(name="a"), String(name="b"))
    res = p_dict.parse_arguments("a=1 b=2".split())
    assert res == dict(a="1", b="2")
    p_dict = ParameterDictionary(Integer(name="a"), Integer(name="b"))
    res = p_dict.parse_arguments("a=1 b=2".split())
    assert res == dict(a=1, b=2)
    # more arguments than those expected
    p_dict = ParameterDictionary(Integer(name="a"))
    with pytest.raises(ValidationError):
        p_dict.parse_arguments("a=1 b=2".split())
    p_dict = ParameterDictionary(
        Integer(name="int"),
        Float(name="float"),
        Bool(name="bool"),
        String(name="string"),
        File(name="file", default="/tmp/file1"),
        Date(name="date"),
        Range(name="range"),
    )
    res = p_dict.parse_arguments("int=1 date=1 bool=1".split())
    assert res == dict(int=1, date="1", bool=True)
    res = p_dict.parse_arguments("int=1 date=1 bool=1".split(), use_defaults=True)
    assert res == dict(
        int=1, date="1", bool=True, extra_scheduler_options="", file="/tmp/file1"
    )
    p_dict2 = ParameterDictionary(
        Bool(name="init"),
        Integer(name="num", default=2, item_separator=",", max_items=1),
    )
    assert p_dict2.parse_arguments("init=0") == dict(init=False)
    assert p_dict2.parse_arguments(
        ["num=0", "num=1", "init=0"], check_errors=False
    ) == dict(num=[0, 1], init=False)
    res = p_dict.parse_arguments(
        "int=1 date=1 bool=1 range=1:5".split(),
        use_defaults=True,
        complete_defaults=True,
    )
    assert res == dict(
        int=1,
        date="1",
        bool=True,
        extra_scheduler_options="",
        range=list(range(1, 6)),
        file="/tmp/file1",
        float=None,
        string=None,
    )

    for arg, parsed_val in [
        ("bool=1", True),
        ("bool=true", True),
        ("bool=TRUE", True),
        ("bool=0", False),
        ("bool=false", False),
        ("bool=False", False),
        ("bool=no", False),
        ("bool=NO", False),
        ("bool=YES", True),
        ("bool", True),  # Special case!
        ("float=1.2", 1.2),
        ("float=-1e-1", -0.1),
        ("float=2E2", 200.0),
        ("string=1", "1"),
        ("string=ä", "ä"),
    ]:
        res = p_dict.parse_arguments(arg.split())
        assert res == {
            arg.split("=")[0]: parsed_val
        }, "Error when parsing %s, got %s" % (arg, res)

    # multiple arguments
    p_dict = ParameterDictionary(
        File(name="file", default="/tmp/file1", max_items=2, item_separator=":"),
        Date(name="date", item_separator="/"),
    )
    assert p_dict.parse_arguments(["file=a:b"]) == dict(file=["a", "b"])
    with pytest.raises(ValidationError):
        p_dict.parse_arguments(["file=a:b:c"])
    with pytest.raises(ValidationError):
        p_dict.parse_arguments(["file=a", "file=b", "file=c"])
    # this should still work since max_items defaults to 1
    # and in that case no splitting happens
    assert p_dict.parse_arguments(["date=a/b"]) == dict(date="a/b")
    assert p_dict.parse_arguments(["file=a", "file=b"]) == dict(file=["a", "b"])


def test_complete(dummy_env):
    from evaluation_system.api.parameters import (
        ParameterDictionary,
        Integer,
        File,
        Date,
    )

    p_dict = ParameterDictionary(
        Integer(name="int"), File(name="file", default="/tmp/file1"), Date(name="date")
    )
    conf = dict(int=1)
    p_dict._complete(conf)
    assert conf == {"int": 1, "extra_scheduler_options": "", "file": "/tmp/file1"}
    p_dict._complete(conf, add_missing_defaults=True)
    assert conf == {
        "int": 1,
        "extra_scheduler_options": "",
        "date": None,
        "file": "/tmp/file1",
    }

    assert p_dict._complete() == {"extra_scheduler_options": "", "file": "/tmp/file1"}
    assert p_dict._complete(add_missing_defaults=True) == {
        "int": None,
        "date": None,
        "extra_scheduler_options": "",
        "file": "/tmp/file1",
    }

    # assure default value gets parsed (i.e. validated) when creating Parameter
    p = ParameterDictionary(Integer(name="a", default="0"))
    assert p._complete(add_missing_defaults=True) == {
        "a": 0,
        "extra_scheduler_options": "",
    }


def test_defaults(dummy_env):
    from evaluation_system.api.parameters import (
        ParameterDictionary,
        Bool,
        Integer,
        File,
        Date,
        Range,
        Float,
        ValidationError,
    )

    # All these should cause no exception
    Bool(name="a", default=True)
    Bool(name="a", default="True")
    Bool(name="a", default="0")
    Float(name="a", default=1.2e-2)
    Float(name="a", default="1.2e-2")
    Integer(name="a", default="1232")
    Range(name="a", default="1:5:100")
    ra = Range(name="a", default="1, 2")
    assert ra.to_str([1, 2]) == "[1, 2]"
    p_dict = ParameterDictionary(
        File(
            name="file",
            default="/tmp/file1",
            mandatory=True,
            max_items=2,
            item_separator=":",
        ),
        Date(name="date", item_separator="/"),
    )
    with pytest.raises(ValidationError):
        p_dict.parse_arguments(["date=2"], use_defaults=False)
    assert p_dict.parse_arguments(["date=2"], use_defaults=True) == {
        "date": "2",
        "extra_scheduler_options": "",
        "file": ["/tmp/file1"],
    }


def test_validate_errors(dummy_env):
    from evaluation_system.api.parameters import (
        ParameterDictionary,
        Integer,
        File,
        Float,
    )

    p_dict = ParameterDictionary(
        Integer(name="int", mandatory=True),
        File(name="file", max_items=2, item_separator=":"),
        Float(name="float", mandatory=True, max_items=2),
    )
    assert p_dict.validate_errors(dict(int=1, float=2.0)) == {}
    assert p_dict.validate_errors({"int": None}) == {
        "too_many_items": [],
        "missing": [("int", 1), ("float", 2)],
    }

    assert p_dict.validate_errors({"int": [1, 2, 3, 4, 5]}) == {
        "too_many_items": [("int", 1)],
        "missing": [("float", 2)],
    }
    assert p_dict.validate_errors({"int": [1, 2, 3, 4, 5]}) == {
        "too_many_items": [("int", 1)],
        "missing": [("float", 2)],
    }


def test_help(dummy_env):
    from evaluation_system.api.parameters import ParameterDictionary, Integer, Float

    p_dict = ParameterDictionary(
        Integer(name="answer", help="just some value", default=42, print_format="%sm"),
        Float(
            name="other",
            help="just some super float",
            default=71.7,
            print_format="%.2f",
        ),
    )


def test_special_cases(dummy_env):
    from evaluation_system.api.parameters import Range

    # test __str__ method of Range()
    test_cases = [
        ("1960:1970", range(1960, 1970 + 1)),
        ("1970,1971,1972", [1970, 1971, 1972]),
        ("1980:5:2000", range(1980, 2000 + 1, 5)),
        ("1970:1971-1970", [1971]),
        ("1950:10:1980,1985-1960:1970", [1950, 1980, 1985]),
    ]
    case_type = Range()
    for case, result in test_cases:
        assert str(case_type.parse(case)) == ",".join(map(str, result))


def test_parameter_options(dummy_env):
    from evaluation_system.api.parameters import SelectField, SolrField

    # Arguments of SelectField
    with pytest.raises(TypeError):
        SelectField()
    opts = {"key": "val"}
    p = SelectField(options=opts)
    assert opts == p.options
    # Arguments of SolrField
    with pytest.raises(TypeError):
        SolrField()
    p = SolrField(facet="variable")
    # defaults:
    options = {
        "group": 1,
        "multiple": False,
        "predefined_facets": None,
        "editable": True,
    }
    for key, val in options.items():
        assert getattr(p, key) == val
    options = {
        "facet": "variable",
        "group": 2,
        "multiple": True,
        "predefined_facets": {"key": "val"},
        "editable": False,
    }
    p = SolrField(**options)
    for key, val in options.items():
        assert getattr(p, key) == val
