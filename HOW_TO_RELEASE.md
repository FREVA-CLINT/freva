# How to issue an freva release in 16 easy steps

 1. Ensure your main branch is synced to upstream:
     ```sh
     git checkout freva-dev
     git pull origin freva-dev
     ```
 2. Look over whats-new.rst and the docs. Make sure "What's New" is complete
    (check the date!) and add the release summary at the top.
    Things to watch out for:
    - Important new features should be highlighted towards the top.
    - Function/method references should include links to the API docs.
 3. Open a MR with the release summary and whatsnew changes; in particular the
    release headline should get feedback from the team on what's important to include.
 4. After merging, again ensure your freva-dev branch is synced to upstream:
     ```sh
     git pull origin freva-dev
     ```
 5. If you have any doubts, run the full test suite one final time!
      ```sh
      make test
      ```
 6. Check that the Docs build is passing on the `freva-dev` branch.
 7. Bump the old version number in `src/evaluation_system/__init__.py` to the
    new version number.
 8. Add a section for the next release {YYMM.minor.p} to doc/whats-new.rst:
     ```rst
     .. _whats-new.YYMM.minor.p+1:

     vYYMM.minro.p+1
     ---------------

     New Features
     ~~~~~~~~~~~~


     Breaking changes
     ~~~~~~~~~~~~~~~~


     Deprecations
     ~~~~~~~~~~~~


     Bug fixes
     ~~~~~~~~~


     Documentation
     ~~~~~~~~~~~~~


     Internal Changes
     ~~~~~~~~~~~~~~~~

     ```
9. Commit your changes and push to main again:
      ```sh
      git commit -am 'New whatsnew section'
      git push upstream freva-dev
      ```
    You're done pushing to freva-dev!

10. Create a new tag on [GitLab](https://gitlab.dkrz.de/freva/evaluation_system/-/tags/new)
    Type in the version number (with a "v")  and paste the release summary in the notes.
11. This should automatically trigger an upload of the new build to GitLab Registry.
    Check this has run [here](https://github.com/pydata/xarray/actions/workflows/pypi-release.yaml),
    and that the version number you expect is displayed [on PyPI](https://pypi.org/project/xarray/)


## Note on version numbering

We utilise a mix of [CALVER](https://calver.org/) and [SEMVER](https://semver.org/)
version system. Specifically, we have adopted the pattern `YYMM.minor.p`, where
`YY` is a 2-digit year (e.g. `22` for 2022), `MM` is a 2-digit zero-padded month
(e.g. `01` for January), minor is the semver minor version and `p` is the
semver patch number (starting at zero at the minor version).
