"""
This module contains functions and classes for parsing files and directories
for file sequences. 

** IMPORTANT **
Currently, the directory scanner skips any links and they will not show up
in any Parser list.
"""

from .config import cfg
from ultrasequence import File, Sequence, Stat
import os
from os import walk
import sys
import logging


logger = logging.getLogger()

if sys.version_info < (3, 5):
	try:
		from scandir import walk
	except ImportError:
		logger.info('For Python versions < 3.5, scandir module is '
					'recommended. Run >>> pip install scandir')


def get_files_in_dir(root, files):
	"""
	Assembles a list of files for a single directory.

	:param root: the the root path to the current directory
	:param files: the list of filenames in the directory
	:return: a list of filenames if cfg.get_stats is False, or a list
			 of tuples (filename, file_stats) if cfg.get_stats is True.
	"""
	dir_list = []
	if cfg.get_stats:
		for file in files:
			abspath = os.path.join(root, file)
			if os.path.islink(abspath):
				continue
			dir_list.append((abspath, os.stat(abspath)))
	else:
		dir_list += [os.path.join(root, file) for file in files
					 if os.path.isfile(os.path.join(root, file))]
	return dir_list


def get_files_in_directory(path):
	"""
	Searches a root directory and returns a list of all files. If 
	cfg.recurse is True, the scanner will descend all child directories.

	:param path: The root path to scan for files
	:return: a list of filenames if cfg.get_stats is False, or a list
			 of tuples (filename, file_stats) if cfg.get_stats is True.
	"""
	file_list = []
	if cfg.recurse:
		for root, dirs, files in walk(path):
			file_list += get_files_in_dir(root, files)
	else:
		file_list += get_files_in_dir(path, os.listdir(path))
	return file_list


def map_stats(stat_order, stats):
	if not len(stat_order) == len(stats):
		raise ValueError('Stat order and stats not the same length.')
	return dict(zip(stat_order, stats))


class Parser(object):
	def __init__(self, include_exts=cfg.include_exts,
				 exclude_exts=cfg.exclude_exts, get_stats=cfg.get_stats,
				 ignore_padding=cfg.ignore_padding):
		"""
		
		:param list include_exts: 
		:param list exclude_exts: 
		:param bool get_stats: 
		:param bool ignore_padding: 
		"""
		if not include_exts or not isinstance(include_exts, (tuple, list)):
			self.include_exts = set()
		else:
			self.include_exts = set(include_exts)

		if not exclude_exts or not isinstance(exclude_exts, (tuple, list)):
			self.exclude_exts = set()
		else:
			self.exclude_exts = set(exclude_exts)

		cfg.get_stats = get_stats
		self.ignore_padding = ignore_padding
		self._reset()

	def _reset(self):
		self._sequences = {}
		self.sequences = []
		self.single_frames = []
		self.non_sequences = []
		self.excluded = []
		self.collisions = []
		self.parsed = False

	def __str__(self):
		return ('Parser(sequences=%d, single_frames=%d, non_sequences=%d, '
				'excluded=%d, collisions=%d)' %
				(len(self.sequences), len(self.single_frames),
				 len(self.non_sequences), len(self.excluded),
				 len(self.collisions)))

	def __repr__(self):
		return ('<Parser object at %s, parsed=%s>' %
				(hex(id(self)), self.parsed))

	def _cleanup(self):
		while self._sequences:
			seq = self._sequences.popitem()[1]
			if seq.frames == 1:
				self.single_frames.append(seq[0])
			else:
				self.sequences.append(seq)
		self.parsed = True

	def _sort_file(self, file_, stats=None):
		file_ = File(file_, stats=stats)

		if self.include_exts and file_.ext.lower() not in self.include_exts \
				or file_.ext.lower() in self.exclude_exts:
			self.excluded.append(file_)

		elif file_.frame is None:
			self.non_sequences.append(file_)

		else:
			seq_name = file_.get_seq_key()
			if seq_name in self._sequences:
				try:
					self._sequences[seq_name].append(file_)
				except IndexError:
					self.collisions.append(file_)
			else:
				self._sequences[seq_name] = Sequence(file_)

	def parse_directory(self, directory, recurse=cfg.recurse):
		"""
		Parse a directory on the file system.

		:param str directory:
		:param bool recurse:
		:return:
		"""
		self._reset()
		cfg.recurse = recurse
		directory = os.path.expanduser(directory)
		if isinstance(directory, str) and os.path.isdir(directory):
			file_list = get_files_in_directory(directory)
			while file_list:  # reduce memory consumption for large lists
				file_ = file_list.pop(0)
				if cfg.get_stats:
					self._sort_file(file_[0], file_[1])
				else:
					self._sort_file(file_)
			self._cleanup()
		else:
			logger.warning('%s is not an available directory.' % directory)

	def parse_file(self, filepath, csv=cfg.csv, csv_sep=cfg.csv_sep,
				   stat_order=cfg.stat_order, date_format=cfg.date_format):
		"""
		Parse a text csv or text file containing file listings.

		:param str filepath: 
		:param bool csv: 
		:param str csv_sep: 
		:param list stat_order: 
		:return: 
		"""
		# Test is stat_order strings are valid
		Stat(dict((x, None) for x in stat_order))

		filepath = os.path.expanduser(filepath)

		self._reset()
		if isinstance(filepath, str) and os.path.isfile(filepath):
			with open(filepath, 'r') as file_list:
				for file_ in file_list:
					if csv:
						file_ = file_.rstrip().split(csv_sep)
						filename = file_[0]
						if cfg.get_stats:
							stats = map_stats(stat_order, file_[1:])
							self._sort_file(filename, stats)
						else:
							self._sort_file(filename)
					else:
						self._sort_file(file_.rstrip())
			self._cleanup()
		else:
			logger.warning('%s is not a valid filepath.' % filepath)

	# def parse_list(self, file_list):
	# 	"""
	# 	Parse a list of files.
	#
	# 	:param file_list:
	# 	:return:
	# 	"""
	# 	pass
