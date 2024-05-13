# HOWTO: Installing and running pytest of the python3 source code

> **_Note:_** The virtual machine is only accessible from within the dkrz network, freva-dev should also be installed from a machine with access to the dkrz internal network (e.g mistral).

# Running the tests

Suppose you have installed the python environment in `Path2Eva`, then you'll only have to submit the following command:

```bash
$: FREVA_ENV=Path2Eva make test
```

### Uploading code coverage results
The test coverage report is uploaded to a swift cloud object container, where it can be displayed in html format.
To upload the test coverage report simply do a
```bash
$: FREVA_ENV=Path2Eva make upload
```

The target container should is located in the *ch1187* project. To upload the content to the cloud container you'll have to give you password.
You also have to be member of the group *ch1187*.

You should then be able to inspect the results on the [public folder](https://swift.dkrz.de/v1/dkrz_3d3c7abc-1681-4012-b656-3cc1058c52a9/freva-dev/public/index.html)
and the [test_results folder](https://swift.dkrz.de/v1/dkrz_3d3c7abc-1681-4012-b656-3cc1058c52a9/freva-dev/test_results/index.html) of the swift browser.


*Note:* The command

```bash
$: FREVA_ENV=Path2Eva make all
```

(without test or upload) will execute both, creating the tests and uploading the results.
