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
`$Pth2Eva/$NameYourEvaluationSystem/freva/`).

You'll then only have to submit the following command:

```bash
$: make test
```

### Uploading code coverage results
The test coverage report is uploaded to a swift cloud object container, where it can be displayed in html format. 
To upload the test coverage report simply do a
```bash
$: make upload
```

The target container should is located in the *ch1187* project. To upload the content to the cloud container you'll have to give you password.
You also have to be member of the group *ch1187*.

You should then be able to inspect the results on the [public folder](https://swift.dkrz.de/v1/dkrz_3d3c7abc-1681-4012-b656-3cc1058c52a9/freva-dev/public/index.html)
and the [test_results folder](https://swift.dkrz.de/v1/dkrz_3d3c7abc-1681-4012-b656-3cc1058c52a9/freva-dev/test_results/index.html) of the swift browser.


*Note:* The command

```bash
$: make
```

(without test or upload) will execute both, creating the tests and uploading the results.
