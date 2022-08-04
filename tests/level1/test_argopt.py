from rs4 import argopt
import pytest
import getopt

def test_argopt_clear ():
    argopt.add_option ("-a", desc = "option a")
    opts = argopt.get_options ("-a".split ())
    assert "-a" in opts

    argopt.clear ()
    opts = argopt.get_options ([])
    assert "-a" not in opts

def test_argopt ():
    argopt.add_option ("-a", "--affix", desc = "option a")
    opts = argopt.get_options ("-a".split ())
    assert "--affix" in opts
    argopt.clear ()

    with pytest.raises (SystemError):
        argopt.add_option ("-a=AA", "--affix", desc = "option a")
    argopt.clear ()

    with pytest.raises (SystemError):
        argopt.add_option ("-a", "--affix=A", desc = "option a")
    argopt.clear ()

    argopt.add_option ("-a=", "--affix=A", desc = "option a")
    with pytest.raises (getopt.GetoptError):
        opts = argopt.get_options ("-a".split ())
    opts = argopt.get_options ("-a 4".split ())
    assert "--affix" in opts
    assert opts.get ("--affix", 4) == '4'
    assert opts.get ("--affix", 4, int) == 4

    opts = argopt.get_options ([])
    assert opts.get ("--affix", 4) == 4
    assert opts.get ("--affix") is None
    with pytest.raises (KeyError):
        assert opts ["--affix"]
    argopt.clear ()

    argopt.add_option ("-a=", "--affix=A", desc = "option a", default = 1)
    opts = argopt.get_options ("-a 4".split ())
    assert opts.get ("--affix", 4) == 4

    opts = argopt.get_options ([])
    assert opts.get ("--affix", 4) == 4
    assert opts.get ("--affix") == 1
    argopt.clear ()

    argopt.add_option ("-a=", "--affix=A", desc = "option a", default = 1)
    opts = argopt.get_options ("-a 4".split ())
    opts.set ("--affix", 6)
    assert opts.get ("--affix") == 6
    assert opts.get ("-a") == 6

    opts ["--affix"] = 8
    assert opts ["--affix"] == 8
    assert opts ["-a"] == 8

    del opts ["--affix"]
    assert "--affix" not in opts
    assert "-a" not in opts
    argopt.clear ()

    argopt.add_option ("-a=", "--affix=A", desc = "option a", default = True)
    opts = argopt.get_options ("-a false".split ())
    assert opts.get ("--affix") is False

    opts = argopt.get_options ("-a 1".split ())
    assert opts.get ("--affix") is True

    opts = argopt.get_options ("-a 2".split ())
    with pytest.raises (ValueError):
        opts.get ("--affix")
    argopt.clear ()
