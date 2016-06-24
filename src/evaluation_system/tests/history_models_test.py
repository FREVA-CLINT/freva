"""
Created on 23.05.2016

@author: Sebastian Illing
"""
import unittest
from datetime import datetime
from evaluation_system.model.history.models import *
from django.contrib.auth.models import User


class Test(unittest.TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='test_user2', password='123')
        self.hist = History.objects.create(
            timestamp=datetime.now(),
            status=History.processStatus.running,
            uid=self.user,
            configuration='{"some": "config", "dict": "values"}',
            tool='dummytool',
            slurm_output='/path/to/slurm-44742.out'
        )

    def tearDown(self):
        self.hist.delete()
        self.user.delete()

    def test_history_model(self):
        # test slurm id
        slurm_id = self.hist.slurmId()
        self.assertEqual(slurm_id, '44742')

        # test status_names
        status = self.hist.status_name()
        self.assertEqual(status, 'running')

        # test print history
        _str = self.hist.__str__(compact=True)

    def test_result_model(self):
        r = Result.objects.create(
            history_id=self.hist,
            output_file='/some/paht/to_file.ext',
            preview_file='/path/to/preview.jpg',
            file_type=Result.Filetype.plot
        )

        self.assertTrue(Result.objects.filter(id=r.id).exists())

        # test get extension
        self.assertEqual(r.fileExtension(), '.ext')