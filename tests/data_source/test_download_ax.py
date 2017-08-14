
import unittest
from kinetic_datanator.data_source import download_ax
import os
import shutil
import json


class TestDownloadExperiments(unittest.TestCase):


	def tearDown(self):
		shutil.rmtree(os.path.join('.', 'AllExperiments'))
		
	def test_download_single_year(self):
		#self.assertTrue(os.path.isdir('./AllSamples'))
		de = download_ax.DownloadExperiments()
		de.download_single_year(2003)
		self.assertTrue(os.path.isdir('./AllExperiments'))
		self.assertTrue(os.path.isfile('./AllExperiments/2003.txt'))
		data = json.loads(open(os.path.join('.', 'AllExperiments/2003.txt'), 'r').read())
		self.assertEqual(data['experiments']['total'], 71)
		self.assertEqual(data['experiments']['total-samples'], 4906)

class TestDownloadSamples(unittest.TestCase):

	def tearDown(self):
		shutil.rmtree(os.path.join('.', 'AllSamples'))

	def test_download_single_sample(self):
		ds = download_ax.DownloadSamples()
		ax_num = 'E-GEOD-662'
		ds.download_single_sample(ax_num)
		self.assertTrue(os.path.isdir('./AllSamples'))
		self.assertTrue(os.path.isfile('./AllSamples/{}.txt'.format(ax_num)))
		data = json.loads(open(os.path.join('./AllSamples', "{}.txt".format(ax_num)), 'r').read())
		self.assertEqual(data['experiment']['accession'], ax_num)

class TestDownloadProtocol(unittest.TestCase):
	def tearDown(self):
		shutil.rmtree(os.path.join('.', 'AllProtocol'))


	def test_download_single_sample(self):
		dp = download_ax.DownloadProtocol()
		ax_num = 'E-GEOD-662'
		dp.download_single_protocol(ax_num)
		self.assertTrue(os.path.isdir('./AllProtocol'))
		self.assertTrue(os.path.isfile('./AllProtocol/{}.txt'.format(ax_num)))
		data = json.loads(open(os.path.join('./AllProtocol', "{}.txt".format(ax_num)), 'r').read())
		protocol_accession_ids = []
		for entry in data['protocols']['protocol']:
			protocol_accession_ids.append(entry['id'])
		self.assertEqual(sorted(protocol_accession_ids), sorted([65183, 65184]))
		print(data)

	





class TestDownloadAllMetadata(unittest.TestCase):
	def tearDown(self):
		shutil.rmtree(os.path.join('.', 'AllExperiments'))
		shutil.rmtree(os.path.join('.', 'AllSamples'))

	def test_download_all_metadata(self):
		download_ax.download_all_metadata(start_year=2001, end_year=2002)

		ax_nums =[u'E-GEOD-10', u'E-GEOD-8', u'E-GEOD-6', u'E-GEOD-92', u'E-GEOD-110', u'E-GEOD-74', u'E-SNGR-7', u'E-SNGR-6', u'E-SNGR-5', u'E-SNGR-4', u'E-SNGR-3', u'E-SNGR-2', u'E-GEOD-42', u'E-GEOD-62', u'E-GEOD-61', u'E-GEOD-60', u'E-GEOD-53', u'E-GEOD-50', u'E-GEOD-49', u'E-GEOD-48', u'E-GEOD-54', u'E-MEXP-18', u'E-GEOD-31', u'E-GEOD-29', u'E-GEOD-23', u'E-GEOD-20']

		for num in ax_nums:
			self.assertTrue(os.path.isfile('./AllSamples/{}.txt'.format(num)))
			self.assertTrue(os.path.isfile('./AllProtocol/{}.txt'.format(num)))