import unittest
from source import tricipy


class TestQualtricsApi(unittest.TestCase):

    base_url = 'https://___.___.qualtrics.com/API/v3/'  # replace with your Qualtrics institution URL
    server_token = '61_______________________________'  # replace with your Qualtrics token
    use_timestamps_for_output_files = False

    def get_survey(self, project_name, survey_token, survey_name, write_to_disk):
        q = tricipy.Qualtrics(project_name=project_name, api_token=self.server_token, base_url=self.base_url,
                              use_timestamps_for_filenames=self.use_timestamps_for_output_files)
        return q.get_survey(survey_token=survey_token, survey_name=survey_name,
                            write_to_disk=write_to_disk)

    def test_survey_project1(self):
        project_name = 'Project 1'  # replace with your desired project name
        survey_token = 'SV________________'  # replace with your Qualtrics survey token
        survey_name = 'Survey 1'  # replace with your Qualtrics survey name
        write_to_disk = True

        survey = self.get_survey(project_name=project_name, survey_token=survey_token, survey_name=survey_name,
                                 write_to_disk=write_to_disk)

        self.assertIsInstance(survey, dict)

    def test_survey_project2(self):
        project_name = 'Project 2'  # replace with your desired project name
        survey_token = 'SV________________'  # replace with your Qualtrics survey token
        survey_name = 'Survey 1'  # replace with your Qualtrics survey name
        write_to_disk = True

        survey = self.get_survey(project_name=project_name, survey_token=survey_token, survey_name=survey_name,
                                 write_to_disk=write_to_disk)

        self.assertIsInstance(survey, dict)

        survey_token = 'SV________________'
        survey_name = 'Survey 2'
        write_to_disk = True

        survey2 = self.get_survey(project_name=project_name, survey_token=survey_token, survey_name=survey_name,
                                  write_to_disk=write_to_disk)

        self.assertIsInstance(survey2, dict)


if __name__ == '__main__':
    unittest.main()


