import requests
import time
import pandas as pd
import zipfile
import StringIO
import json
import os
import feather
import argparse as ap
import datetime
import sys
import traceback

class Qualtrics:
    def __init__(self, api_token, project_name, base_url, path_to_output_files='../data_out', content_type="json",
                 use_timestamps_for_filenames=False):
        """
            Class for accessing Qualtrics using the v3 API
            Ref: https://api.qualtrics.com/docs/overview

        :param api_token: Global API token to be used in the token header (not the survey specific token)
        :param project_name: Global project name to organize multiple surveys into a single folder name
        :param base_url: Common qualtrics url for various API resources (suffices to be appended to this
        :param path_to_output_files: Directory to place output
        :param content_type: JSON is default (no others yet supported)
        :param use_timestamps_for_filenames: True/False to add hour/min/secs to each output date in filename
        """
        self.__api_token_header = {"x-api-token": api_token, "Content-Type": "application/" + content_type}
        self.__project_name = project_name
        self.__base_url = base_url
        self.__path_to_output_files = path_to_output_files
        self.__use_timestamps = use_timestamps_for_filenames

        if self.__base_url[-1] != "/":
            self.__base_url += "/"

    def get_responseexports(self, survey_token, survey_name, write_to_disk, get_survey=False,
                            result_format="json", max_wait_ms=20000, sleep_ms=1, **kwargs):
        """
            Ref: https://api.qualtrics.com/docs/json
            Get the actual respondent data for any survey using the survey_token, known in Qualtrics as the surveyId.

        :param survey_token:  "SV_xx"
        :param survey_name: e.g., "My First Survey"
        :param write_to_disk: True/False to convert pandas dataframe to feather format and save to disk
        :param result_format:
        :param max_wait_ms: Number of millisecs to wait for a response before abandoning the API query
        :param sleep_ms:
        :param kwargs: Various parameters to limit the number of responses from the API
        :return: If not writing to disk, returns a dict, else writes to disk and returns nothing
        """

        url_suffix = 'responseexports'
        form_fields = {"surveyId": survey_token, "format": result_format.lower()}

        # Ref: https://api.qualtrics.com/docs/json

        if 'lastResponseId' in kwargs:
            form_fields['lastResponseId'] = kwargs['lastResponseId']

        if 'startDate' in kwargs:
            form_fields['startDate'] = kwargs['startDate']

        if 'endDate' in kwargs:
            form_fields['endDate'] = kwargs['endDate']

        if 'limit' in kwargs:
            form_fields['limit'] = kwargs['limit']

        if 'includedQuestionIds' in kwargs:
            form_fields['includedQuestionIds'] = kwargs['includedQuestionIds']

        if 'useLabels' in kwargs:
            form_fields['useLabels'] = kwargs['useLabels']
        else:
            form_fields['useLabels'] = True

        if 'useLocalTime' in kwargs:
            form_fields['useLocalTime'] = kwargs['useLocalTime']
        else:
            form_fields['useLocalTime'] = False

        full_url = self.__base_url + url_suffix

        export_response_handle = requests.post(full_url, json=form_fields, headers=self.__api_token_header)

        if export_response_handle.ok:  # For successful API call, response code will be 200 (OK)
            sleep_counter_ms = 0

            if url_suffix[-1] != '/':
                url_suffix += '/'

            export_status_url = self.__base_url + url_suffix.lower() + export_response_handle.json()['result']['id']

            while sleep_counter_ms <= max_wait_ms:
                response_status_json = requests.get(export_status_url, headers=self.__api_token_header).json()

                if response_status_json['result']['percentComplete'] == 100:
                    break

                sleep_counter_ms += sleep_ms
                time.sleep(sleep_ms)

            r = requests.get(response_status_json['result']['file'], stream=True, headers=self.__api_token_header)

            # Ref: https://docs.python.org/2/library/zipfile.html#zipfile-objects, http://stackoverflow.com/a/14260592
            sio = StringIO.StringIO(r.content)
            z = zipfile.ZipFile(sio)  # zipped data needs to be unzipped
            response_data = z.read(z.NameToInfo.keys()[0])

        else:
            export_response_handle.raise_for_status()

        response_data_json = json.loads(response_data)['responses']

        filename = ' '

        if write_to_disk:
            dataframe = self.create_df_from_api_data(response_data_json)
            filename = self.write_df_to_disk(dataframe=dataframe, survey_name=survey_name, url_suffix=url_suffix)
        else:
            print 'Retrieved responseexports data for ' + survey_name

        if get_survey:
            self.get_survey(survey_token=survey_token, survey_name=survey_name, write_to_disk=write_to_disk)

        return response_data_json, filename

    def get_survey(self, survey_token, survey_name, write_to_disk):
        """
            Retrieve the survey questions and response options in json format (not user responses)
            Call this method directly or indirectly from the get_responseexports method:
                Indirectly is convenient for writing json to disk.
                Directly is required to receive the json object directly as a returned object.
            Ref: https://api.qualtrics.com/docs/get-survey

        :param survey_token:  Used as the API token to retrieve the survey questions/answer formats
        :param survey_name:  Used to name the output file
        :param write_to_disk:  True writes json to disk, False returns json data

        :return: Survey question and response text--does not contain actual respondent data
        """

        full_url = self.__base_url + 'surveys/' + survey_token
        response_data = requests.get(full_url, headers=self.__api_token_header)

        # data = response_data.content
        response_data_json = json.loads(response_data.content)['result']  # return just result if other branches are desired

        if write_to_disk:
            if not isinstance(self.__path_to_output_files, str):
                raise ValueError('path_to_files argument must be a string')
            if not os.path.isdir(os.path.realpath(self.__path_to_output_files)):
                raise ValueError('path_to_files argument is invalid.  Please check the supplied path, where the output'
                                 'files should be written to disk.')
            elif self.__path_to_output_files[-1] != os.path.sep:
                self.__path_to_output_files += '/'

            path = self.setup_output_filename(base_path=self.__path_to_output_files, survey_name=survey_name,
                                              type='survey', extension='json')

            self.write_json_to_disk(json_data=response_data_json, full_file_path=path)
        else:
            print 'Retrieved survey data for ' + survey_name

        return response_data_json

    def write_json_to_disk(self, json_data, full_file_path):
        """
            Given json data as input, write to disk
        :param json_data:  The data to be written to disk
        :param full_file_path:  Complete file path to write, including file name
        :return:
        """
        with open(full_file_path, 'w') as outfile:
            try:
                json.dump(json_data, outfile, sort_keys=True, indent=4, ensure_ascii=True)
                print ' '.join([os.path.abspath(full_file_path), 'written to disk'])
            except:
                # exc_type, exc_value, exc_traceback = sys.exc_info()
                # print "*** print_tb:"
                # traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                # print "*** print_exception:"
                # traceback.print_exception(exc_type, exc_value, exc_traceback,
                #                           limit=2, file=sys.stdout)
                # print "*** print_exc:"
                # traceback.print_exc()

                raise ValueError('Unable to write json output to disk at ' + os.path.abspath(full_file_path))

    def create_df_from_api_data(self, json_data):
        """
            Given json data as input, create a pandas dataframe
        :param json_data:
        :return:
        """

        if isinstance(json_data, list):
            response_data_pd = pd.DataFrame(json_data, )
        elif isinstance(json_data, dict):
            # project_pd = pd.DataFrame.from_records(value[u'responses'])
            response_data_pd = pd.DataFrame(json_data.items())
            # project_pd = pd.DataFrame.from_records(value, orient='columns')
        elif isinstance(json_data, pd.DataFrame):
            response_data_pd = json_data
        else:
            raise ValueError("Need to add a new type of dataframe object value to the code.")

        # df = pd.read_json(response_data_pd)

        # .applymap() converts all zero length strings to ' '.  Feather segfaults if it encounters ''
        response_data_pd = response_data_pd.applymap(lambda x: x.replace('', ' ') if x == '' else x)

        return response_data_pd

    def write_df_to_disk(self, dataframe, survey_name, url_suffix):
        """
            Given a pandas dataframe, write df to disk in feather format
        :param dataframe:  Pandas df
        :return:  NA
        """

        path_to_files = self.__path_to_output_files

        if not isinstance(path_to_files, str):
            raise ValueError('path_to_files argument must be a string')
        if not os.path.isdir(os.path.realpath(path_to_files)):
            raise ValueError('path_to_files argument is invalid.  Please check the supplied path, where the output'
                             'files should be written to disk.')
        elif path_to_files[-1] != os.path.sep:
            path_to_files += '/'

        path = self.setup_output_filename(base_path=path_to_files, survey_name=survey_name,
                                          type=url_suffix.split('/')[0], extension='feather')

        try:
            feather.write_dataframe(dataframe, path)
            print ' '.join([os.path.abspath(path), 'written to disk'])
        except:
            raise ValueError('Unable to write feather output to disk')

        return path

    def setup_output_filename(self, base_path, survey_name, type, extension):
        """

        :param base_path:  Main output directory
        :param survey_name:  Subfolder which is the project name
        :param type:  Typically the API url_suffix, e.g., responseexports
        :param extension:  Filename extension, e.g., "feather"
        :return:  The complete path
        """

        sub_folder = base_path + self.__project_name

        if not os.path.exists(sub_folder):
            os.mkdir(sub_folder)

        if not self.__use_timestamps:
            today = datetime.datetime.now().strftime("%Y%m%d")
        else:
            now = datetime.datetime.now()
            today = '_'.join([now.strftime("%Y%m%d"), now.strftime("%H%M%S")])

        path = sub_folder + '/' + today + '_' + survey_name + '_' + type + '.' + extension

        return path


def create_parser():
    """
        This construction allows unittest to pass in command line arguments to this program
        Ref: http://dustinrcollins.com/testing-python-command-line-apps
    :return: ArgumentParser object
    """

    # Change these defaults as needed
    base_url = 'https://___.___.qualtrics.com/API/v3/'
    path_to_output_files = '../data_out'

    parser = ap.ArgumentParser(description='Retrieve data via the Qualtrics APIs')

    parser.add_argument('-b', '--base_url', required=False, type=str,
                        help=''.join(['Base URL, e.g., \"', base_url, '\"']))
    parser.add_argument('-j', '--project_name', required=True, type=str,
                        help=''.join(['Project Name, not necessarily the survey name, for folder organization of related surveys']))
    parser.add_argument('-u', '--url_suffix', required=True, type=str,
                        help='URL, e.g., responseexports, appended to the base url')
    parser.add_argument('-t', '--survey_token', required=True, type=str,
                        help='The Qualtrics survey API token, e.g., SV_xxxxxxxxxxxxxxxxxx')
    parser.add_argument('-n', '--survey_name', required=True, type=str,
                        help='The Qualtrics named survey, e.g., \"My Example Project\"')
    parser.add_argument('-s', '--server_token', required=True, type=str,
                        help='Example Server API Token for Qualtrics: 61xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxyZ')
    parser.add_argument('-p', '--path_to_output_files', required=False, type=str,
                        default=path_to_output_files,
                        help='Absolute or relative path to write file output')
    parser.add_argument('-w', '--write_to_disk', required=False,
                        action='store_true',
                        help='Write results to disk if specified (no argument required)')
    parser.add_argument('-i', '--use_timestamps_for_filenames', required=False,
                        action='store_true',
                        help='Add hour/mins/secs to output file names (no argument required)')

    return parser


if __name__ == '__main__':
    base_url = ''
    project_name = ''
    url_suffix = ''
    api_token = ''
    survey_name = ''
    write_to_disk = False
    use_timestamps_for_filenames = False
    get_survey = False

    parser = create_parser()
    args = parser.parse_args()

    if args.base_url:
        base_url = args.base_url

    if args.project_name:
        project_name = args.project_name

    if args.url_suffix:
        url_suffix = args.url_suffix

    if args.survey_token:
        survey_token = args.survey_token

    if args.survey_name:
        survey_name = args.survey_name

    if args.server_token:
        server_token = args.server_token

    if args.path_to_output_files:
        file_output_path = args.path_to_output_files

    if args.write_to_disk:
        write_to_disk = True

    if args.use_timestamps_for_filenames:
        use_timestamps_for_filenames = True

    q = Qualtrics(api_token=server_token, project_name=project_name, base_url=base_url,
                  path_to_output_files=file_output_path, use_timestamps_for_filenames=use_timestamps_for_filenames)

    if url_suffix.lower() == 'responseexports':
        responseexports = q.get_responseexports(url_suffix=url_suffix, survey_token=survey_token,
                                                survey_name=survey_name, get_survey=get_survey,
                                                write_to_disk=write_to_disk)
