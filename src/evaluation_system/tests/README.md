# HOWTO: Installing and running pytest of the python3 source code

## Installing the freva development version
To install the python3 verion, which is currently still unter development
you have to use the `install_freva-dev.sh` in the `build` directory.
It should be sufficient to only set the `Path2Eva` and the `USERRESULTDIR`,
environment variables (if desired). A test servers for apache solr and mariadb
are up and running on the virtual machine www-regiklim.dkrz.de. Since this
virtual machine is only accessible from within the dkrz network freva-dev
should also from a machine with access to the dkrz internal network (e.g mistral).

## Running the tests

To run the test change into the newly created freva-dev instance located in
`$Pth2Eva/$NameYourEvaluationSystem/freva/src/evaluation_system`.
You'll then only have to submit the following command:

```bash

$: make test

```
