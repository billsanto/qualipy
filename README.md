# Qualipy
Access survey data via the Qualtrics v3 API using Python 2.7.

Currently, this will retrieve response data and survey content only.  

Command line usage example (See create_parser method in the source for a description of options):

python qualipy.py --base_url "https://x.y.qualtrics.com/API/v3/" --project_name "My Project Name" --url_suffix responseexports --survey_name "My Survey Name" --server_token 61__________________ --survey_token SV________________ --get_survey --write_to_disk

When responseexports is used as the url_suffix, response data will be retrieved from the server.  In addition, if --get_survey is specified, and --write_to_disk is specified too, then the questions will be saved to a .json file.  When writing to disk, the response data is first converted to a pandas dataframe before saving in the [feather](https://github.com/wesm/feather) ([Apache Arrow](https://arrow.apache.org/)) format.  The survey questions are saved to disk in their native json format.

Alternately, one may import this code and access the get_responseexports and get_survey methods separately, in which case a pandas dataframe and json object will be returned directly, rather than importing the data files from disk.

A template for a unit test in provided in the tests folder.
