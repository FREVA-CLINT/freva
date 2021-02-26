# HOWTO: Installing and running pytest of the python3 source code

## Installing the freva development version
To get the devlopment branch of freva clone `update_tests` branch of Freva

```bash
$: git clone -b update_tests https://gitlab.dkrz.de/freva/evaluation_system.git
```

or check out the `update_tests` branch you have an existing freva source.

```bash
$: git checkout update_tests
```

To install the development (python3) verion, navigte the the `build` folder
and execute the `install_freva-dev.sh`

```bash
$: ./install_freva-dev.sh
```

Before install the latest freva dev version you might want to set follwing
variables in the `install_freva-dev.sh` script:

- `Path2Eva`: The path where the actual freva instance will be installed to
- `USERRESULTDIR` : Directory for storing user data.

Test servers for apache solr and mariadb are up and running on the virtual
machine *www-regiklim.dkrz.de*. Since this

> **_Note:_** The virtual machine is only accessible from within the dkrz network, freva-dev should also be installed from a machine with access to the dkrz internal network (e.g mistral).

## Running the tests

The install script will run the tests automatically. If you chnage the source
code and want to run the tests again navigate into your install directory (
`$Pth2Eva/$NameYourEvaluationSystem/freva/src/evaluation_system`). 

You'll then only have to submit the following command:

```bash
$: make test
```

### Uploading code coverage results
Gitlab pages seems not to work at the moment. For the time being we can try
to upload the code coverage report to a swift container. To do that change into
the `$Pth2Eva/$NameYourEvaluationSystem` directory and load the drkz `swift` module

```bash
$: module load swift
```

The target container should is located in the *ch1187* project. If you are prompted
that your token has expired renew it by

```bash
$: swift token-new
```

and choose *ch1187* as account, followed by your login credentials. 

To upload the test report simply type

```bash
$: swift upload freva-dev public
```

You should then be able to inspect the results on the [public swift browser](https://swift.dkrz.de/v1/dkrz_3d3c7abc-1681-4012-b656-3cc1058c52a9/freva-dev/public/index.html)
