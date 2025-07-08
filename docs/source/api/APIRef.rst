Databrowser Rest API
====================
The Freva Databrowser REST API is a powerful tool that enables you to search
for climate and environmental datasets seamlessly in various programming
languages. By generating RESTful requests, you can effortlessly access
collections of various datasets, making it an ideal resource for
climate scientists, researchers, and data enthusiasts.

The API's flexible design allows you to perform searches for climate datasets
in a wide range of programming languages. By generating RESTful requests,
you can easily integrate the API into your preferred language and environment.
Whether you use Python, JavaScript, R, Julia, or any other language with HTTP
request capabilities, the Freva Databrowser REST API accommodates your needs.



.. _databrowser-api-overview:

Getting an overview
-------------------

.. http:get:: /api/freva-nextgen/databrowser/overview

    This endpoint allows you to retrieve an overview of the different
    Data Reference Syntax (DRS) standards implemented in the Freva Databrowser
    REST API. The DRS standards define the structure and metadata organisation
    for climate datasets, and each standard offers specific attributes for
    searching and filtering datasets.

    :statuscode 200: no error
    :resheader Content-Type: ``application/json``: the available DRS search standards
                             and their search facets.

                             - ``flavours``: array of available DRS standards.
                             - ``attributes``: array of search facets for each available DRS standard.

    Example Request
    ~~~~~~~~~~~~~~~

    .. sourcecode:: http

        GET /api/freva-nextgen/databrowser/overview HTTP/1.1
        Host: www.freva.dkrz.de

    Example Response
    ~~~~~~~~~~~~~~~~

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
              "flavours": [
                "freva",
                "cmip6",
                "cmip5",
                "cordex",
                "nextgems",
                "user"
              ],
              "attributes": {
                "freva": [
                  "experiment",
                  "ensemble",
                  "fs_type",
                  "grid_label",
                  "institute",
                  "model",
                  // ... (other facets)
                ],
                "cmip6": [
                  "experiment_id",
                  "member_id",
                  "fs_type",
                  "grid_label",
                  "institution_id",
                  "source_id",
                  "mip_era",
                  "activity_id",
                  // ... (other facets)
                ],
                  // ... (other DRS standards)
              }
            }


    Code examples
    ~~~~~~~~~~~~~
    Below you can find example usages of this request in different scripting and
    programming languages

    .. tabs::

        .. code-tab:: bash
            :caption: Shell

            # Parse the json-content with jq
            curl -X GET \
                https://www.freva.dkrz.de/api/freva-nextgen/databrowser/overview | jq .attributes.cordex

        .. code-tab:: python
            :caption: Python

            import requests
            response = requests.get("https://www.freva.dkrz.de/api/freva-nextgen/databrowser/overview")
            data = response.json()

        .. code-tab:: r
            :caption: gnuR

            library(httr)
            response <- GET("https://www.freva.dkrz.de/api/freva-nextgen/databrowser/overview")
            data <- jsonlite::fromJSON(content(response, as = "text", encoding = "utf-8"))

        .. code-tab:: julia
            :caption: Julia

            using HTTP
            using JSON
            response = HTTP.get("https://www.freva.dkrz.de/api/freva-nextgen/databrowser/overview")
            data = JSON.parse(String(HTTP.body(response)))

        .. code-tab:: c
            :caption: C/C++

            #include <stdio.h>
            #include <curl/curl.h>

            int main() {
                CURL *curl;
                CURLcode res;

                curl = curl_easy_init();
                if (curl) {
                    char url[] = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/overview";

                    curl_easy_setopt(curl, CURLOPT_URL, url);
                    res = curl_easy_perform(curl);
                    curl_easy_cleanup(curl);
                }

                return 0;
            }

---

.. _databrowser-api-search:

Searching for datasets locations
---------------------------------

.. http:get:: /api/freva-nextgen/databrowser/data-search/(str:flavour)/(str:uniq_key)

    This endpoint allows you to search for climate datasets based on the specified
    Data Reference Syntax (DRS) standard (`flavour`) and the type of search result
    (`uniq_key`), which can be either "file" or "uri". The `databrowser` method
    provides a flexible and efficient way to query datasets matching specific search
    criteria and retrieve a list of data files or locations that meet the query
    parameters.

    :param flavour: The Data Reference Syntax (DRS) standard specifying the
                    type of climate datasets to query. The available
                    DRS standards can be retrieved using the
                    ``GET /overview`` method.
    :type flavour: str
    :param uniq_key: The type of search result, which can be either "file" or
                    "uri". This parameter determines whether the search
                    will be based on file paths or Uniform Resource
                    Identifiers (URIs).
    :type uniq_key: str
    :query start: Specify the starting point for receiving search results.
                 Default is 0.
    :type start: int
    :query multi-version: Use versioned datasets for querying instead of the
                          latest datasets. Default is false.
    :type multi-version: bool
    :query \**search_facets: With any other query parameters you refine your
                             data search. Query parameters could be, depending
                             on the DRS standard flavour ``product``, ``project``
                             ``model`` etc.

    :statuscode 200: no error
    :statuscode 422: invalid query parameters
    :resheader Content-Type: ``text/plain``: `stream` providing a list of data
                              files or locations that match the search criteria.




    Example Request
    ~~~~~~~~~~~~~~~

    Here's an example of how to use this endpoint with additional parameters.
    In this example we use the `freva` DRS standard and search for `file` entries.
    Here we also want to get only those datasets that belong to the ``EUR-11``
    ``product`` and are store in the cloud (``fs_type=swift``)

    .. sourcecode:: http

        GET /api/freva-nextgen/databrowser/data-search/freva/file?product=EUR-11&fs_type=swift HTTP/1.1
        Host: www.freva.dkrz.de

    Example Response
    ~~~~~~~~~~~~~~~~

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: plain/text

        https://swift.dkrz.de/v1/dkrz_a32dc0e8-2299-4239-a47d-6bf45c8b0160/freva_test/model/
        regional/cordex/output/EUR-11/GERICS/NCC-NorESM1-M/rcp85/r1i1p1/GERICS-REMO2015/v1/
        3hr/pr/v20181212/pr_EUR-11_NCC-NorESM1-M_rcp85_r1i1p1_GERICS-REMO2015_v2_3hr_200701
        020130-200701020430.zarr\n
        https://swift.dkrz.de/v1/dkrz_a32dc0e8-2299-4239-a47d-6bf45c8b0160/freva_test/model/
        regional/cordex/output/EUR-11/CLMcom/MPI-M-MPI-ESM-LR/historical/r1i1p1/CLMcom-CCLM4-8-17/
        v1/day/tas/v20140515/tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r1i1p1_CLMcom-CCLM4-8-17_v1_
        day_194912011200-194912101200.zarr\n

    Code examples
    ~~~~~~~~~~~~~
    Below you can find example usages of this request in different scripting and
    programming languages.

    .. tabs::

        .. code-tab:: bash
            :caption: Shell

            curl -X GET \
            'https://www.freva.dkrz.de/api/freva-nextgen/databrowser/data-search/freva/file?product=EUR-11&fs_type=swift'

        .. code-tab:: python
            :caption: Python

            import requests
            response = requests.get(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/data-search/freva/file",
                params={"product": "EUR-11", "fs_type": "swift"}
            )
            data = list(response.iter_lines(decode_unicode=True))

        .. code-tab:: r
            :caption: gnuR

            library(httr)
            response <- GET(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/data-search/freva/file",
                query = list(product = "EUR-11", fs_type = "swift")
            )
            data <- strsplit(content(response, as = "text", encoding = "UTF-8"), "\n")[[1]]



        .. code-tab:: julia
            :caption: Julia

            using HTTP
            response = HTTP.get(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/data-search/freva/file",
                query = Dict("product" => "EUR-11", "fs_type" => "swift")
            )
            data = split(String(HTTP.body(response)),"\n")

        .. code-tab:: c
            :caption: C/C++

            #include <stdio.h>
            #include <curl/curl.h>

            int main() {
                CURL *curl;
                CURLcode res;
                const char *url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/data-search/freva/file";

                // Query parameters
                const char *product = "EUR-11";
                const char *fs_type = "swift"
                const int start = 0;
                const int multi_version = 0; // 0 for false, 1 for true

                // Build the query string
                char query[256];
                snprintf(query, sizeof(query),
                    "?product=%s&fs_type=%s&start=%d&multi-version=%d",product, fs_type , start, multi_version);

                // Initialize curl
                curl = curl_easy_init();
                if (!curl) {
                    fprintf(stderr, "Failed to initialize curl\n");
                    return 1;
                }

                // Construct the full URL with query parameters
                char full_url[512];
                snprintf(full_url, sizeof(full_url), "%s%s", url, query);

                // Set the URL to fetch
                curl_easy_setopt(curl, CURLOPT_URL, full_url);

                // Perform the request
                res = curl_easy_perform(curl);
                if (res != CURLE_OK) {
                    fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
                }

                // Clean up
                curl_easy_cleanup(curl);

                return 0;
            }

---

The `databrowser` endpoint provides a powerful tool to search for climate
datasets based on various criteria. By using this method, you can efficiently
retrieve a list of data files or locations that match your specific requirements.
Make the most of the `databrowser` endpoint to access valuable climate data
effortlessly in the Freva Databrowser REST API!


.. _databrowser-api-search_facets:

Searching for metadata
----------------------

.. http:get:: /api/freva-nextgen/databrowser/metadata-search/(str:flavour)/(str:uniq_key)

    This endpoint allows you to search metadata (facets) based on the
    specified Data Reference Syntax (DRS) standard (`flavour`) and the type of
    search result (`uniq_key`), which can be either `file` or `uri`.
    Facets represent the metadata categories associated with the climate datasets,
    such as experiment, model, institute, and more. This method provides a
    comprehensive view of the available facets and their corresponding counts
    based on the provided search criteria.

    :param flavour: The Data Reference Syntax (DRS) standard specifying the
                    type of climate datasets to query. The available
                    DRS standards can be retrieved using the
                    ``GET /overview`` method.
    :type flavour: str
    :param uniq_key: The type of search result, which can be either "file" or
                    "uri". This parameter determines whether the search
                    will be based on file paths or Uniform Resource
                    Identifiers (URIs).
    :type uniq_key: str
    :query multi-version: Use versioned datasets for querying instead of the
                          latest datasets. Default is false.
    :type multi-version: bool
    :query facets: The facets that should be part of the output, by default
                    all facets will be returned.
    :type facets: str, list
    :query translate: Translate the metadata output to the required DRS flavour.
                      Default is true
    :type translate: bool
    :query \**search_facets: With any other query parameters you refine your
                             data search. Query parameters could be, depending
                             on the DRS standard flavour ``product``, ``project``
                             ``model`` etc.
    :type \**search_facets: str, list[str]

    :statuscode 200: no error
    :statuscode 422: invalid query parameters
    :resheader Content-Type: ``application/json``: Metadata matching the data
                             query.

                             - ``total_count``: Number of dataset found for
                             - ``facets``: Table of occurring metadata facets.
                               each facet entry contains a list of facet values
                               followed by the number of occurrences of this
                               facet.
                             - ``facet_mapping``: Translation rules describing
                               how to map the freva DRS standard to the desired
                               standard. This can be useful if ``GET /search_facets``
                               was instructed to *not* translate the facet entries
                               and the translation should be done from client side.
                             - ``primary_facets``: Array of facets that are most
                               important. This can be useful for building clients
                               that should hide lesser used metadata by default.

    Example Request
    ~~~~~~~~~~~~~~~

    Here's an example of how to use this endpoint with additional parameters.
    In this example we use the `freva` DRS standard and search for `file` entries.
    Here we also want to get only those datasets that belong to the ``EUR-11``
    ``product``.

    .. sourcecode:: http

        GET /api/freva-nextgen/databrowser/metadata-search/freva/file?product=EUR-11 HTTP/1.1
        Host: www.freva.dkrz.de

    Example Response
    ~~~~~~~~~~~~~~~~

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
           "total_count": 7,
           "facets": {
               "cmor_table": ["1day", "3", "3hr", "3", "fx", "1"],
               "dataset": ["cordex-fs", "3", "cordex-hsm", "2", "cordex-swfit", "2"],
               "driving_model": ["mpi-m-mpi-esm-lr", "4", "ncc-noresm1-m", "3"],
               "ensemble": ["r0i0p0", "1", "r1i1p1", "6"],
               "experiment": ["historical", "4", "rcp85", "3"],
               "format": ["nc", "5", "zarr", "2"],
               "fs_type": ["posix", "7"],
               "grid_id": [],
               "grid_label": ["gn", "7"],
               "institute": ["clmcom", "4", "gerics", "3"],
               "level_type": ["2d", "7"],
               "model": ["mpi-m-mpi-esm-lr-clmcom-cclm4-8-17-v1", "4", "ncc-noresm1-m-gerics-remo2015-v1", "3"],
               "product": ["eur-11", "7"],
               "project": ["cordex", "7"],
               "rcm_name": ["clmcom-cclm4-8-17", "4", "gerics-remo2015", "3"],
               "rcm_version": ["v1", "7"],
               "realm": ["atmos", "7"],
               "time_aggregation": ["avg", "7"],
               "time_frequency": ["1day", "3", "3hr", "3", "fx", "1"],
               "variable": ["orog", "1", "pr", "3", "tas", "3"]
           },
           "facet_mapping": {
               "experiment": "experiment",
               "ensemble": "ensemble",
               "fs_type": "fs_type",
               "grid_label": "grid_label",
               "institute": "institute",
               "model": "model",
               "project": "project",
               "product": "product",
               "realm": "realm",
               "variable": "variable",
               "time_aggregation": "time_aggregation",
               "time_frequency": "time_frequency",
               "cmor_table": "cmor_table",
               "dataset": "dataset",
               "driving_model": "driving_model",
               "format": "format",
               "grid_id": "grid_id",
               "level_type": "level_type",
               "rcm_name": "rcm_name",
               "rcm_version": "rcm_version"
           },
           "primary_facets": ["experiment", "ensemble", "institute", "model", "project", "product", "realm", "time_aggregation", "time_frequency"]
        }

    Code examples
    ~~~~~~~~~~~~~
    Below you can find example usages of this request in different scripting and
    programming languages.


    .. tabs::

        .. code-tab:: bash
            :caption: Shell

            curl -X GET 'https://www.freva.dkrz.de/api/freva-nextgen/databrowser/metadata-search/freva/file?product=EUR-11'


        .. code-tab:: python
            :caption: Python

            import requests
            response = requests.get(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/metadata-search/freva/file",
                params={"product": "EUR-11"}
            )
            data = response.json()

        .. code-tab:: r
            :caption: gnuR

            library(httr)
            response <- GET(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/metadata-search/freva/file",
                query = list(product = "EUR-11")
            )
            data <- jsonlite::fromJSON(content(response, as = "text", encoding = "utf-8"))

        .. code-tab:: julia
            :caption: Julia

            using HTTP
            using JSON
            response = HTTP.get(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/metadata-search/freva/file",
                query = Dict("product" => "EUR-11")
            )
            data = JSON.parse(String(HTTP.body(response)))

        .. code-tab:: c
            :caption: C/C++

            #include <stdio.h>
            #include <curl/curl.h>

            int main() {
                CURL *curl;
                CURLcode res;
                const char *url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/metadata-search/freva/file";

                // Query parameters
                const char *product = "EUR-11";

                // Build the query string
                char query[256];
                snprintf(query, sizeof(query), "?product=%s", product);

                // Initialize curl
                curl = curl_easy_init();
                if (!curl) {
                    fprintf(stderr, "Failed to initialize curl\n");
                    return 1;
                }

                // Construct the full URL with query parameters
                char full_url[512];
                snprintf(full_url, sizeof(full_url), "%s%s", url, query);

                // Set the URL to fetch
                curl_easy_setopt(curl, CURLOPT_URL, full_url);

                // Perform the request
                res = curl_easy_perform(curl);
                if (res != CURLE_OK) {
                    fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
                }

                // Clean up
                curl_easy_cleanup(curl);

                return 0;
            }


---

.. _databrowser-api-intake:

Generating an intake-esm catalogue
----------------------------------

.. http:get:: /api/freva-nextgen/databrowser/intake-catalogue/(str:flavour)/(str:uniq_key)

    This endpoint generates an intake-esm catalogue in JSON format from a `freva`
    search. The catalogue includes metadata about the datasets found in the search
    results. Intake-esm is a data cataloging system that allows easy organization,
    discovery, and access to Earth System Model (ESM) data. The generated catalogue
    can be used by tools compatible with intake-esm, such as Pangeo.

    :param flavour: The Data Reference Syntax (DRS) standard specifying the
                    type of climate datasets to query. The available
                    DRS standards can be retrieved using the
                    ``GET /api/datasets/overview`` method.
    :type flavour: str
    :param uniq_key: The type of search result, which can be either "file" or
                    "uri". This parameter determines whether the search
                    will be based on file paths or Uniform Resource
                    Identifiers (URIs).
    :type uniq_key: str
    :query start: Specify the starting point for receiving search results.
                 Default is 0.
    :type start: int
    :query max-results: Raise an Error if more results are found than that
                        number, -1 for do not raise at all.
    :type max-results: int
    :query multi-version: Use versioned datasets for querying instead of the
                          latest datasets. Default is false.
    :type multi-version: bool
    :query translate: Translate the metadata output to the required DRS flavour.
                      Default is true
    :type translate: bool
    :query \**search_facets: With any other query parameters you refine your
                             data search. Query parameters could be, depending
                             on the DRS standard flavour ``product``, ``project``
                             ``model`` etc.
    :type \**search_facets: str, list[str]

    :statuscode 200: no error
    :statuscode 400: no entries found for this query
    :statuscode 422: invalid query parameters
    :resheader Content-Type: ``application/json``: the intake-esm catalogue


    Example Request
    ~~~~~~~~~~~~~~~

    Here's an example of how to use this endpoint with additional parameters.
    In this example we want to create an intake-catalogue that follows the
    `freva` DRS standard and points to data files rather than uris.
    Here we also want to get only those datasets that belong to the ``EUR-11``
    ``product``.

    .. sourcecode:: http

        GET /api/freva-nextgen/databrowser/intake-catalogue/freva/file?product=EUR-11 HTTP/1.1
        Host: www.freva.dkrz.de

    Example Response
    ~~~~~~~~~~~~~~~~

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
             "esmcat_version": "0.1.0",
             "attributes": [
               {
                 "column_name": "project",
                 "vocabulary": ""
               },
               {
                 "column_name": "product",
                 "vocabulary": ""
               },
               {
                 "column_name": "institute",
                 "vocabulary": ""
               },
               // ... (other attributes)
             ],
             "assets": {
               "column_name": "uri",
               "format_column_name": "format"
             },
             "id": "freva",
             "description": "Catalogue from freva-databrowser v2023.4.1",
             "title": "freva-databrowser catalogue",
             "last_updated": "2023-07-26T10:50:18.592898",
             "aggregation_control": {
               // ... (aggregation options)
             },
             "catalog_dict": [
               {
                 "file": "https://swift.dkrz.de/v1/...",
                 "project": ["cordex"],
                 "product": ["EUR-11"],
                 "institute": ["GERICS"],
                 "model": ["NCC-NorESM1-M-GERICS-REMO2015-v1"],
                 "experiment": ["rcp85"],
                 "time_frequency": ["3hr"],
                 "realm": ["atmos"],
                 "variable": ["pr"],
                 "ensemble": ["r1i1p1"],
                 "cmor_table": ["3hr"],
                 "fs_type": "posix",
                 "grid_label": ["gn"]
               },
               // ... (other datasets)
             ]
           }


    Example
    ~~~~~~~
    Below you can find example usages of this request in different scripting and
    programming languages.

    .. tabs::

        .. code-tab:: bash
            :caption: Shell

            curl -X GET \
            'https://www.freva.dkrz.de/api/freva-nextgen/databrowser/intake-catalogue/freva/file?product=EUR-11' > catalogue.json

        .. code-tab:: python
            :caption: Python

            import requests
            import intake
            response = requests.get(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/intake-catalogue/freva/file",
                params={"product": "EUR-11"}
            )
            cat = intake.open_esm_datastore(cat)

        .. code-tab:: r
            :caption: gnuR

            library(httr)
            response <- GET(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/intake-catalogue/freva/file",
                query = list(product = "EUR-11")
            )
            json_content <- content(response, "text", encoding="utf-8")
            write(json_content, file = "intake-catalogue.json")

        .. code-tab:: julia
            :caption: Julia

            using HTTP
            using JSON
            response = HTTP.get(
                "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/intake-catalogue/freva/file",
                query = Dict("product" => "EUR-11")
            )
            data = JSON.parse(String(HTTP.body(response)))
            open("intake-catalogue.json", "w") do io
                write(io, JSON.json(data))
            end

        .. code-tab:: c
            :caption: C/C++

            #include <stdio.h>
            #include <curl/curl.h>

            int main() {
                CURL *curl;
                CURLcode res;
                FILE *fp;

                curl = curl_easy_init();
                if (curl) {
                    char url[] = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/intake-catalogue/freva/file?product=EUR-11";
                    curl_easy_setopt(curl, CURLOPT_URL, url);

                    fp = fopen("intake-catalogue.json", "w");
                    curl_easy_setopt(curl, CURLOPT_WRITEDATA, fp);

                    res = curl_easy_perform(curl);
                    if (res != CURLE_OK) {
                        printf("Error: %s\n", curl_easy_strerror(res));
                    }

                    curl_easy_cleanup(curl);
                    fclose(fp);
                }
                return 0;
            }

---

.. _databrowser-api-zarr:

Creating zarr endpoints for streaming data
-------------------------------------------

.. http:get:: /api/freva-nextgen/databrowser/load/(str:flavour)

   This endpoint searches for datasets and streams the results as Zarr data.
   The Zarr format allows for efficient storage and retrieval of large,
   multidimensional arrays. This endpoint can be used to query datasets and
   receive the results in a format that is suitable for further analysis and
   processing with Zarr. If the ``catalogue-type`` parameter is set to "intake",
   it can generate Intake-ESM catalogues that point to the generated Zarr
   endpoints.

   :param flavour: The Data Reference Syntax (DRS) standard specifying the
                   type of climate datasets to query. The available
                   DRS standards can be retrieved using the
                   ``GET /api/datasets/overview`` method.
   :type flavour: str
   :query start: Specify the starting point for receiving search results.
                Default is 0.
   :type start: int
   :type max-results: int
   :query multi-version: Use versioned datasets for querying instead of the
                         latest datasets. Default is false.
   :type multi-version: bool
   :query translate: Translate the metadata output to the required DRS flavour.
                     Default is true
   :type translate: bool
   :query catalogue-type: Set the type of catalogue you want to create from
                          this query.
   :type catalogue-type: str
   :query \**search_facets: With any other query parameters you refine your
                            data search. Query parameters could be, depending
                            on the DRS standard flavour ``product``, ``project``
                            ``model`` etc.
   :type \**search_facets: str, list[str]
   :reqheader Authorization: Bearer token for authentication.
   :reqheader Content-Type: application/json

   :statuscode 200: no error
   :statuscode 400: no entries found for this query
   :statuscode 422: invalid query parameters
   :resheader Content-Type: ``text/plain``: zarr endpoints for the data


   Example Request
   ~~~~~~~~~~~~~~~

   The logic works just like for the ``data-search`` and ``intake-catalogue``
   endpoints. We constrain the data search by ``key=value`` search pairs.
   The only difference is that we have to authenticate by using an access token.
   You will also have to use a valid access token if you want to access the
   zarr data via http. Please refer to the `authentication <https://freva-clint.github.io/freva-nextgen/auth/index.html>`__
   chapter for more details.

   .. sourcecode:: http

       GET /api/freva-nextgen/databrowser/load/freva/file?dataset=cmip6-fs HTTP/1.1
       Host: www.freva.dkrz.de
       Authorization: Bearer your_access_token

   Example Response
   ~~~~~~~~~~~~~~~~

   .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: plain/text

       https://www.freva.dkrz.de/api/freva-nextgen/data-portal/zarr/dcb608a0-9d77-5045-b656-f21dfb5e9acf.zarr
       https://www.freva.dkrz.de/api/freva-nextgen/data-portal/zarr/f56264e3-d713-5c27-bc4e-c97f15b5fe86.zarr


   Example
   ~~~~~~~
   Below you can find example usages of this request in different scripting and
   programming languages.

   .. tabs::

       .. code-tab:: bash
           :caption: Shell

           curl -X GET \
           'https://www.freva.dkrz.de/api/freva-nextgen/databrowser/load/freva?dataset=cmip6-fs'
            -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

       .. code-tab:: python
           :caption: Python

           import requests
           import intake
           response = requests.get(
               "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/load/freva",
               params={"dataset": "cmip6-fs"},
               headers={"Authorization": "Bearer YOUR_ACCESS_TOKEN"},
               stream=True,
           )
           files = list(res.iterlines(decode_unicode=True)

       .. code-tab:: r
           :caption: gnuR

           library(httr)
           response <- GET(
               "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/load/freva",
               query = list(dataset = "cmip6-fs")
           )
           data <- strsplit(content(response, as = "text", encoding = "UTF-8"), "\n")[[1]]


       .. code-tab:: julia
           :caption: Julia

           using HTTP
           response = HTTP.get(
               "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/load/freva",
               query = Dict("dataset" => "cmip6-fs")
           )
           data = split(String(HTTP.body(response)),"\n")

       .. code-tab:: c
           :caption: C/C++

           #include <stdio.h>
           #include <curl/curl.h>

           int main() {
               CURL *curl;
               CURLcode res;
               const char *url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/load/freva";

               // Query parameters
               const char *dataset = "cmip6-fs";
               const int start = 0;
               const int multi_version = 0; // 0 for false, 1 for true

               // Build the query string
               char query[256];
               snprintf(query, sizeof(query),
                   "?dataset=%s&start=%d&multi-version=%d",product , start, multi_version);

               // Initialize curl
               curl = curl_easy_init();
               if (!curl) {
                   fprintf(stderr, "Failed to initialize curl\n");
                   return 1;
               }

               // Construct the full URL with query parameters
               char full_url[512];
               snprintf(full_url, sizeof(full_url), "%s%s", url, query);

               // Set the URL to fetch
               curl_easy_setopt(curl, CURLOPT_URL, full_url);

               // Perform the request
               res = curl_easy_perform(curl);
               if (res != CURLE_OK) {
                   fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
               }

               // Clean up
               curl_easy_cleanup(curl);

               return 0;
           }

.. _databrowser-api-userdata:

---

Adding and deleting User Data in Databrowser
---------------------------------------------

.. http:post:: /api/freva-nextgen/databrowser/userdata

   This endpoint allows authenticated users to add metadata about their own data to the databrowser. Users provide a list of metadata entries and optional facets for indexing and searching their datasets.

   :reqbody user_metadata: A list of metadata entries about the user's data to be added. Each entry must include the required fields: **file**, **variable**, **time**, and **time_frequency**.
   :type user_metadata: list[dict[str, str]]

   :reqbody facets: Optional key-value pairs representing metadata search attributes. These facets are used for indexing and searching the data.
   :type facets: dict[str, Any]

   :reqheader Authorization: Bearer token for authentication.
   :reqheader Content-Type: application/json

   :statuscode 202: Request accepted, returns status message indicating ingestion results.
   :statuscode 422: Invalid request parameters.
   :statuscode 500: Failed to add user data due to a server error.

   Example Request
   ~~~~~~~~~~~~~~~~

   The user must authenticate using a valid access token. The metadata entries and facets are included in the JSON body of the request.

   .. sourcecode:: http

       POST /api/freva-nextgen/databrowser/userdata HTTP/1.1
       Host: www.freva.dkrz.de
       Authorization: Bearer YOUR_ACCESS_TOKEN
       Content-Type: application/json

       {
           "user_metadata": [
               {
                   "file": "/data/file1.nc",
                   "variable": "tas",
                   "time": "[1979-01-16T12:00:00Z TO 1979-11-16T00:00:00Z]",
                   "time_frequency": "mon",
                   "additional_info": "Sample data file"
               }
           ],
           "facets": {
               "project": "user-data",
               "product": "new",
               "institute": "globe"
           }
       }

   Example Response (Success)
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~

   .. sourcecode:: http

       HTTP/1.1 202 Accepted
       Content-Type: application/json

       {
           "status": "Your data has been successfully added to the databrowser. (Ingested 5 files into Solr and MongoDB)"
       }

   Example Response (No Files)
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   .. sourcecode:: http

       HTTP/1.1 202 Accepted
       Content-Type: application/json

       {
           "status": "No data was added to the databrowser. (No files ingested into Solr and MongoDB)"
       }


   Example
   ~~~~~~~

   Below you can find example usages of this request in different scripting and programming languages.

   .. tabs::

       .. code-tab:: bash
           :caption: Shell

           curl -X POST \
           'https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata' \
           -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
           -H "Content-Type: application/json" \
           -d '{
               "user_metadata": [
                   {
                       "file": "/data/file1.nc",
                       "variable": "tas",
                       "time": "[1979-01-16T12:00:00Z TO 1979-11-16T00:00:00Z]",
                       "time_frequency": "mon",
                       "additional_info": "Sample data file"
                   }
               ],
               "facets": {
                   "project": "user-data",
                   "product": "new",
                   "institute": "globe"
               }
           }'

       .. code-tab:: python
           :caption: Python

           import requests

           url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata"
           headers = {
               "Authorization": "Bearer YOUR_ACCESS_TOKEN",
               "Content-Type": "application/json"
           }
           data = {
               "user_metadata": [
                   {
                       "file": "/data/file1.nc",
                       "variable": "tas",
                       "time": "[1979-01-16T12:00:00Z TO 1979-11-16T00:00:00Z]",
                       "time_frequency": "mon",
                       "additional_info": "Sample data file"
                   }
               ],
               "facets": {
                   "project": "user-data",
                   "product": "new",
                   "institute": "globe"
               }
           }

           response = requests.post(url, headers=headers, json=data)
           print(response.json())

       .. code-tab:: r
           :caption: R

           library(httr)

           url <- "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata"
           headers <- c(Authorization = "Bearer YOUR_ACCESS_TOKEN")
           body <- list(
               user_metadata = list(
                   list(
                       file = "/data/file1.nc",
                       variable = "tas",
                       time = "[1979-01-16T12:00:00Z TO 1979-11-16T00:00:00Z]",
                       time_frequency = "mon",
                       additional_info = "Sample data file"
                   )
               ),
               facets = list(
                   project = "user-data",
                   product = "new",
                   institute = "globe"
               )
           )

           response <- POST(url, add_headers(.headers = headers), body = body, encode = "json")
           content <- content(response, "parsed")
           print(content)

       .. code-tab:: julia
           :caption: Julia

           using HTTP, JSON

           url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata"
           headers = Dict(
               "Authorization" => "Bearer YOUR_ACCESS_TOKEN",
               "Content-Type" => "application/json"
           )
           body = JSON.json(Dict(
               "user_metadata" => [
                   Dict(
                       "file" => "/data/file1.nc",
                       "variable" => "tas",
                       "time" => "[1979-01-16T12:00:00Z TO 1979-11-16T00:00:00Z]",
                       "time_frequency" => "mon",
                       "additional_info" => "Sample data file"
                   )
               ],
               "facets" => Dict(
                   "project" => "user-data",
                   "product" => "new",
                   "institute" => "globe"
               )
           ))

           response = HTTP.request("POST", url, headers = headers, body = body)
           println(String(response.body))

       .. code-tab:: c
           :caption: C/C++

           #include <stdio.h>
           #include <curl/curl.h>

           int main() {
               CURL *curl;
               CURLcode res;

               const char *url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata";
               const char *token = "YOUR_ACCESS_TOKEN";
               const char *json_data = "{"
                   "\"user_metadata\": ["
                       "{"
                           "\"file\": \"/data/file1.nc\","
                           "\"variable\": \"tas\","
                           "\"time\": \"[1979-01-16T12:00:00Z TO 1979-11-16T00:00:00Z]\","
                           "\"time_frequency\": \"mon\","
                           "\"additional_info\": \"Sample data file\""
                       "}"
                   "],"
                   "\"facets\": {"
                       "\"project\": \"user-data\","
                       "\"product\": \"new\","
                       "\"institute\": \"globe\""
                   "}"
               "}";

               // Initialize curl
               curl = curl_easy_init();
               if (curl) {
                   struct curl_slist *headers = NULL;
                   headers = curl_slist_append(headers, "Content-Type: application/json");
                   char auth_header[256];
                   snprintf(auth_header, sizeof(auth_header), "Authorization: Bearer %s", token);
                   headers = curl_slist_append(headers, auth_header);

                   // Set the URL
                   curl_easy_setopt(curl, CURLOPT_URL, url);

                   // Set headers
                   curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

                   // Set the HTTP method to POST
                   curl_easy_setopt(curl, CURLOPT_POST, 1L);

                   // Set the JSON data to send
                   curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_data);

                   // Perform the request
                   res = curl_easy_perform(curl);
                   if (res != CURLE_OK) {
                       fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
                   }

                   // Clean up
                   curl_slist_free_all(headers);
                   curl_easy_cleanup(curl);
               }
               return 0;
           }

.. http:delete:: /api/freva-nextgen/databrowser/userdata

   This endpoint allows authenticated users to delete their previously indexed data from the databrowser. Users specify search keys to identify the data entries they wish to remove.

   :reqbody search_keys: Search keys (key-value pairs) used to identify the data to delete.
   :type search_keys: dict[str, Any]

   :reqheader Authorization: Bearer token for authentication.
   :reqheader Content-Type: application/json

   :statuscode 202: User data has been deleted successfully.
   :statuscode 500: Failed to delete user data due to a server error.

   Example Request
   ~~~~~~~~~~~~~~~

   The user must authenticate using a valid access token. The search keys are provided in the JSON body of the request to specify which data entries to delete.

   .. sourcecode:: http

       DELETE /api/freva-nextgen/databrowser/userdata HTTP/1.1
       Host: www.freva.dkrz.de
       Authorization: Bearer YOUR_ACCESS_TOKEN
       Content-Type: application/json

       {
           "project": "user-data",
           "product": "new",
           "institute": "globe"
       }

   Example Response
   ~~~~~~~~~~~~~~~~

   .. sourcecode:: http

       HTTP/1.1 202 Accepted
       Content-Type: application/json

       {
           "status": "User data has been deleted successfully"
       }

   Example
   ~~~~~~~

   Below you can find example usages of this request in different scripting and programming languages.

   .. tabs::

       .. code-tab:: bash
           :caption: Shell

           curl -X DELETE \
           'https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata' \
           -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
           -H "Content-Type: application/json" \
           -d '{
               "project": "user-data",
               "product": "new",
               "institute": "globe"
           }'

       .. code-tab:: python
           :caption: Python

           import requests

           url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata"
           headers = {
               "Authorization": "Bearer YOUR_ACCESS_TOKEN",
               "Content-Type": "application/json"
           }
           data = {
               "project": "user-data",
               "product": "new",
               "institute": "globe"
           }

           response = requests.delete(url, headers=headers, json=data)
           print(response.json())

       .. code-tab:: r
           :caption: R

           library(httr)

           url <- "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata"
           headers <- c(Authorization = "Bearer YOUR_ACCESS_TOKEN")
           body <- list(
               project = "user-data",
               product = "new",
               institute = "globe"
           )

           response <- DELETE(url, add_headers(.headers = headers), body = body, encode = "json")
           content <- content(response, "parsed")
           print(content)

       .. code-tab:: julia
           :caption: Julia

           using HTTP, JSON

           url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata"
           headers = Dict(
               "Authorization" => "Bearer YOUR_ACCESS_TOKEN",
               "Content-Type" => "application/json"
           )
           body = JSON.json(Dict(
               "project" => "user-data",
               "product" => "new",
               "institute" => "globe"
           ))

           response = HTTP.request("DELETE", url, headers = headers, body = body)
           println(String(response.body))

       .. code-tab:: c
           :caption: C/C++

           #include <stdio.h>
           #include <curl/curl.h>

           int main() {
               CURL *curl;
               CURLcode res;

               const char *url = "https://www.freva.dkrz.de/api/freva-nextgen/databrowser/userdata";
               const char *token = "YOUR_ACCESS_TOKEN";
               const char *json_data = "{"
                   "\"project\": \"user-data\","
                   "\"product\": \"new\","
                   "\"institute\": \"globe\""
               "}";

               // Initialize curl
               curl = curl_easy_init();
               if (curl) {
                   struct curl_slist *headers = NULL;
                   headers = curl_slist_append(headers, "Content-Type: application/json");
                   char auth_header[256];
                   snprintf(auth_header, sizeof(auth_header), "Authorization: Bearer %s", token);
                   headers = curl_slist_append(headers, auth_header);

                   // Set the URL
                   curl_easy_setopt(curl, CURLOPT_URL, url);

                   // Set headers
                   curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

                   // Set the HTTP method to DELETE
                   curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "DELETE");

                   // Set the JSON data to send
                   curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_data);

                   // Perform the request
                   res = curl_easy_perform(curl);
                   if (res != CURLE_OK) {
                       fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
                   }

                   // Clean up
                   curl_slist_free_all(headers);
                   curl_easy_cleanup(curl);
               }
               return 0;
           }

---


.. note::
   Please note that in these examples,
   "https://www.freva.dkrz.de" were used as a placeholder URL.
   You should replace it with the actual URL of your
   Freva Databrowser REST API. The responses above are truncated for brevity.
   The actual response will include more datasets in the `catalog_dict` list.
