try:
	import configparser
except ImportError:
	import ConfigParser as configparser
import os


class Config(object):
	def __init__(self):
		self.default_config = {
			'global': {
				'recurse': 'false',
				'ignore_padding': 'true',
				'include_exts': '',
				'exclude_exts': '',
			},
			'stats': {
				'get_stats': 'false',
				'stat_order': '',
			},
			'csv': {
				'csv': 'false',
				'csv_sep': r'\t'
			}
		}
		self.user_config_file = os.path.expanduser('~/.useq.ini')
		self.default_parser = configparser.ConfigParser()
		self.default_parser.read_dict(self.default_config)
		self._load_config(self.default_parser)
		self._load_user_config()

	def __repr__(self):
		return (
			'Config({recurse=%s, ignore_padding=%s, include_exts=%s,'
			'exclude_exts=%s, get_stats=%s, stat_order=%s, csv=%s, '
			'csv_sep=%s)' %
			(self.recurse, self.ignore_padding, self.include_exts,
			 self.exclude_exts, self.get_stats, self.stat_order, self.csv,
			 self.csv_sep))

	def _load_config(self, cfgparser):
		self.recurse = cfgparser['global'].getboolean('recurse')
		self.ignore_padding = cfgparser['global'].getboolean('ignore_padding')
		self.include_exts = cfgparser['global']['include_exts'].split()
		self.exclude_exts = cfgparser['global']['exclude_exts'].split()
		self.get_stats = cfgparser['stats'].getboolean('get_stats')
		self.stat_order = cfgparser['stats']['stat_order'].split()
		self.csv = cfgparser['csv'].getboolean('csv')
		self.csv_sep = cfgparser['csv']['csv_sep']

	def _load_user_config(self):
		if os.path.exists(self.user_config_file):
			cfgparser = configparser.ConfigParser()
			cfgparser.read(self.user_config_file)
			self._load_config(cfgparser)

	def reset_defaults(self):
		self._load_config(self.default_parser)

	def write_user_config(self):
		with open(self.user_config_file, 'w') as f:
			self.default_parser.write(f)
		print('Made user config file at %s' % cfg.user_config_file)


cfg = Config()


# wrapper for __init__ import
def write_user_config():
	cfg.write_user_config()
