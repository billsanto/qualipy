# qualipy
Access survey data via the Qualtrics v3 API using Python 2.7

Currently, this will retrieve response data and survey content only.

Command line usage example (See create_parser method for all options):

python qualipy.py --base_url "https://___.___.qualtrics.com/API/v3/" --project_name "My Project Name" --url_suffix responseexports --survey_name "My Survey Name" --server_token 61__________________ --survey_token SV________________ --get_survey --write_to_disk

A template for a unit test in provided in the tests folder.
