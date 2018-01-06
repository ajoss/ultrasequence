from .config import cfg
import os
import re
import logging


logger = logging.getLogger(__name__)


def extract_frame(name):
	"""
	This function extracts the last set of digits in the string name and
	assumes it is the frame number when returning the parts.

	It's a good idea to only pass basenames without extenions so it doesn't
	attempt to sequence directory names or digits in the extension.

	:param str name: file basename without dir or extension
	:return: 3-pair tuple consisting of the head (all characters preceding the
			 last set of digits, the frame number (last set of digits), and
			 tail (all digits succeeding the frame number).
	"""
	frame_match = re.match(cfg.frame_extract_re, name)
	if frame_match:
		groups = frame_match.groups()
		head, tail = groups[cfg.head_group], groups[cfg.tail_group]
		frame = groups[cfg.frame_group]
	else:
		head, frame, tail = (name, '', '')
	if head is None:
		head = ''
	return head, frame, tail


def split_extension(filename):
	"""
	Splits the extension off the filename and returns a tuple of the
	base filename and the extension (without the dot).
	"""
	parts = filename.split('.')
	if len(parts) < 2:
		return parts[0], ''
	ext = parts.pop(-1)
	head = '.'.join(parts)
	return head, ext


def frame_ranges_to_string(frame_list):
	"""
	Take a flat list of ordered numbers and make a string representation
	of the ranges.

	:param iterable frame_list: sorted list of frame numbers
	:return: string of broken frame ranges (i.e '[10-14, 16, 20-25]')
	"""
	if not frame_list:
		return '[]'
	if not isinstance(frame_list, list):
		frame_list = list(frame_list)
	ranges = [[frame_list.pop(0)]]
	range_i = 0
	for x in frame_list:
		if x - 1 == ranges[range_i][-1]:
			ranges[range_i].append(x)
		else:
			range_i += 1
			ranges.append([x])
	list_of_ranges = []
	for x in ranges:
		if len(x) > 1:
			list_of_ranges.append('-'.join([str(x[0]), str(x[-1])]))
		else:
			list_of_ranges.append(str(x[0]))
	complete_string = '[' + ', '.join(list_of_ranges) + ']'
	return complete_string


class Stat(object):
	"""
	This class mocks object returned by os.stat on Unix platforms. The File
	class passes dicts with **kwargs and iterables with *args. When passing
	an iterable to File class, make sure the stats are int-like items in
	the same order as the params in Stat.__init__.

	"""

	def __init__(self, size=None, inode=None, ctime=None, mtime=None,
				 atime=None, mode=None, dev=None, nlink=None, uid=None,
				 gid=None):
		self.st_size = size
		self.st_ino = inode
		self.st_nlink = nlink
		self.st_dev = dev
		self.st_mode = mode
		self.st_uid = uid
		self.st_gid = gid
		self.st_ctime = ctime
		self.st_mtime = mtime
		self.st_atime = atime

	def __getattr__(self, item):
		ints = ['st_size', 'st_ino', 'st_nlink', 'st_dev', 'st_mode',
				'st_uid', 'st_gid']
		floats = ['st_ctime', 'st_mtime', 'st_atime']
		try:
			if item in ints:
				return int(super(Stat, self).__getattribute__(item))
			elif item in floats:
				return float(super(Stat, self).__getattribute__(item))
		except TypeError:
			return None


class File(object):
	def __init__(self, filepath, stats=None, get_stats=None):
		"""
		Class which represents single files or frames on disk.
		While initializing this object, it can be fed stat values
		directly or can attempt to call them on the fly by setting
		get_stats to True.

		When passing data into the stat argument, the object passed
		in can be either an actual os.stat_result object, a dictionary
		mapping that matches the sequencer.Stat parameter names, or an
		iterable of int like items that matches the order of the
		sequencer.Stat class params in the __init__ method.

		:param str filepath: the absolute filepath of the file
		:param stats: dict or iterable to map to sequencer.Stat params
			or os.stat_result object.
		:param bool get_stats: when True, attempt to call os.stat on the file.
			If file does not exists, revert back to applying stats values
			if they were supplied.
		"""
		if get_stats is not None and isinstance(get_stats, bool):
			cfg.get_stats = get_stats
		self.abspath = filepath
		self.path, self.name = os.path.split(filepath)
		self._base, self.ext = split_extension(self.name)

		parts = extract_frame(self._base)
		self.namehead, self._framenum, tail = parts
		self.head = os.path.join(self.path, self.namehead)
		if not self.ext:
			self.tail = ''
		else:
			self.tail = '.'.join([tail, self.ext])
		self.padding = len(self._framenum)

		try:
			if get_stats:
				try:
					stats = os.stat(filepath)
				except FileNotFoundError:
					if stats is None:
						raise TypeError
			if isinstance(stats, os.stat_result):
				self.stat = stats
			elif isinstance(stats, dict):
				self.stat = Stat(**stats)
			elif isinstance(stats, (list, tuple)):
				self.stat = Stat(*stats)
			else:
				raise TypeError
		except TypeError:
			self.stat = Stat()

	def __str__(self):
		return self.abspath

	def __repr__(self):
		return "File('%s')" % self.abspath

	def __lt__(self, other):
		if isinstance(other, File) \
				and self.get_seq_key() == other.get_seq_key():
			return self.frame_as_str < other.frame_as_str
		else:
			raise TypeError('%s not File instance.' % str(other))

	def __gt__(self, other):
		if isinstance(other, File) \
				and self.get_seq_key() == other.get_seq_key():
			return self.frame_as_str > other.frame_as_str
		else:
			raise TypeError('%s not File instance.' % str(other))

	def __le__(self, other):
		if isinstance(other, File) \
				and self.get_seq_key() == other.get_seq_key():
			return self.frame_as_str <= other.frame_as_str
		else:
			raise TypeError('%s not File instance.' % str(other))

	def __ge__(self, other):
		if isinstance(other, File) \
				and self.get_seq_key() == other.get_seq_key():
			return self.frame_as_str >= other.frame_as_str
		else:
			raise TypeError('%s not File instance.' % str(other))

	def __eq__(self, other):
		if isinstance(other, File):
			return self.abspath == other.abspath
		elif isinstance(other, str):
			return self.abspath == other
		else:
			return False

	def __ne__(self, other):
		if isinstance(other, File):
			return self.abspath != other.abspath
		elif isinstance(other, str):
			return self.abspath != other
		else:
			return True

	@property
	def frame(self):
		""" Integer frame number """
		try:
			return int(self._framenum)
		except ValueError:
			return None

	@property
	def frame_as_str(self):
		""" String frame number extracted from original filename """
		return self._framenum

	@property
	def size(self):
		""" Stat size of file on disk. None if stat not run or supplied. """
		if not self.stat.st_size:
			try:
				self.stat.st_size = os.stat(self.abspath).st_size
				return self.stat.st_size
			except FileNotFoundError:
				return
		else:
			return self.stat.st_size

	@property
	def inode(self):
		""" Stat inode of file on disk. None if stat not run or supplied. """
		if not self.stat.st_ino:
			try:
				self.stat.st_ino = os.stat(self.abspath).st_ino
				return self.stat.st_ino
			except FileNotFoundError:
				return
		else:
			return self.stat.st_ino

	@property
	def nlink(self):
		""" Stat nlink of file on disk. None if stat not run or supplied. """
		if not self.stat.st_nlink:
			try:
				self.stat.st_nlink = os.stat(self.abspath).st_nlink
				return self.stat.st_nlink
			except FileNotFoundError:
				return
		else:
			return self.stat.st_nlink

	@property
	def dev(self):
		""" Stat dev of file on disk. None if stat not run or supplied. """
		if not self.stat.st_dev:
			try:
				self.stat.st_dev = os.stat(self.abspath).st_dev
				return self.stat.st_dev
			except FileNotFoundError:
				return
		else:
			return self.stat.st_dev

	@property
	def mode(self):
		""" Stat mode of file on disk. None if stat not run or supplied. """
		if not self.stat.st_mode:
			try:
				self.stat.st_mode = os.stat(self.abspath).st_mode
				return self.stat.st_mode
			except FileNotFoundError:
				return
		else:
			return self.stat.st_mode

	@property
	def uid(self):
		""" Stat uid of file on disk. None if stat not run or supplied. """
		if not self.stat.st_uid:
			try:
				self.stat.st_uid = os.stat(self.abspath).st_uid
				return self.stat.st_gid
			except FileNotFoundError:
				return
		else:
			return self.stat.st_uid

	@property
	def gid(self):
		""" Stat gid of file on disk. None if stat not run or supplied. """
		if not self.stat.st_gid:
			try:
				self.stat.st_gid = os.stat(self.abspath).st_gid
				return self.stat.st_gid
			except FileNotFoundError:
				return
		else:
			return self.stat.st_gid

	@property
	def ctime(self):
		""" Stat ctime of file on disk. None if stat not run or supplied. """
		if not self.stat.st_ctime:
			try:
				self.stat.st_ctime = os.stat(self.abspath).st_ctime
				return self.stat.st_ctime
			except FileNotFoundError:
				return
		else:
			return self.stat.st_ctime

	@property
	def mtime(self):
		""" Stat mtime of file on disk. None if stat not run or supplied. """
		if not self.stat.st_mtime:
			try:
				self.stat.st_mtime = os.stat(self.abspath).st_mtime
				return self.stat.st_mtime
			except FileNotFoundError:
				return
		else:
			return self.stat.st_mtime

	@property
	def atime(self):
		""" Stat atime of file on disk. None if stat not run or supplied. """
		if not self.stat.st_atime:
			try:
				self.stat.st_atime = os.stat(self.abspath).st_atime
				return self.stat.st_atime
			except FileNotFoundError:
				return
		else:
			return self.stat.st_atime

	def get_seq_key(self, ignore_padding=None):
		"""
		Make sequence name identifier

		:param bool ignore_padding: enforce padding
		:return: sequence name with '#' for frame number if padding ignored
			or standard padding format '%0#d' where '#' is padding amount.
		"""
		if ignore_padding is None or not isinstance(ignore_padding, bool):
			ignore_padding = cfg.ignore_padding
		if not self._framenum:
			digits = ''
		elif ignore_padding is True:
			digits = '#'
		elif ignore_padding is False:
			digits = '%%0%dd' % self.padding
		else:
			raise TypeError('ignore_padding argument must be of type bool.')
		return self.head + digits + self.tail


class Sequence(object):
	def __init__(self, file=None, ignore_padding=None):
		"""
		Class representing a sequence of matching file names. The frames
		are stored in a dictionary with the frame numbers as keys. Sets
		are used for fast operations in calculating missing frames.

		:param file: File object or filename string to base the object
			instantiation off of.
		:param bool ignore_padding: Setting to False will disallow
			new frames from being appended if the frame padding differs.
		"""
		if ignore_padding is not None and isinstance(ignore_padding, bool):
			cfg.ignore_padding = ignore_padding
		self._frames = {}
		self.seq_name = ''
		self.path = ''
		self.namehead = ''
		self.head = ''
		self.tail = ''
		self.ext = ''
		self.padding = 0
		self.inconsistent_padding = False
		if file is not None:
			self.append(file)

	def __str__(self):
		return self.format(cfg.format)

	def __repr__(self):
		return "Sequence('%s', frames=%d)" % (
			self.format(cfg.format), self.frames)

	def __len__(self):
		return len(self._frames)

	def __iter__(self):
		return iter([self._frames[frame] for frame in self._frames])

	def __getitem__(self, frames):
		all_frames = list(sorted(self._frames))
		if isinstance(frames, slice):
			return [self._frames[f] for f in sorted(self._frames)][frames]
		return self._frames[all_frames[frames]]

	def __lt__(self, other):
		if isinstance(other, str):
			return self.seq_name < other
		else:
			return self.seq_name < other.seq_name

	@property
	def abspath(self):
		return self.seq_name

	@property
	def name(self):
		return os.path.basename(self.seq_name)

	@property
	def start(self):
		""" First frame of sequence """
		return min(self._frames)

	@property
	def end(self):
		""" Last frame of sequence """
		return max(self._frames)

	@property
	def frames(self):
		""" Number of total frames actually in sequence """
		return len(self)

	@property
	def frame_numbers(self):
		return list(sorted(self._frames))

	@property
	def implied_frames(self):
		""" Number of expected frames in sequence """
		return self.end - self.start + 1

	@property
	def missing_frames(self):
		""" Number of missing frames in sequence """
		return self.end - (self.start - 1) - self.frames

	@property
	def is_missing_frames(self):
		""" True if non-contiguous portions of the frame numbers """
		return self.frames != self.implied_frames

	@property
	def size(self):
		""" Sum of all filesizes in sequence if available """
		try:
			return sum([file.size for file in self])
		except TypeError:
			return

	def get_frame(self, frame):
		return self._frames[frame]

	def get_frames(self, start=None, end=None, step=1):
		"""  """
		frame_list = []
		if start is None:
			return self[:]
		elif end is not None:
			for frame in range(start, end + 1, step):
				if frame in self._frames:
					frame_list.append(self._frames[frame])
				else:
					logger.warning('Cannot get frame %d not in sequence %s.' %
								   (frame, str(self)))
		return frame_list

	def get_missing_frames(self):
		""" Get list of frame numbers missing between start and end frame """
		implied = range(self.start, self.end + 1)
		return [frame for frame in implied if frame not in self._frames]

	def append(self, file):
		"""
		Add a new frame to the sequence.

		:param file: File object or string to append to Sequence
		"""
		if not isinstance(file, File):
			if isinstance(file, str):
				file = File(file)
				if len(self._frames) > 0 and file.get_seq_key(
						cfg.ignore_padding) != self.seq_name:
					raise ValueError('%s is not a member of %s. Not appending.'
									 % (file, repr(self)))
		if file.frame is None:
			raise ValueError('%s can not be sequenced.' % str(file))
		if not self.frames:
			self.namehead = file.namehead
			self.path = file.path
			self.head = file.head
			self.tail = file.tail
			self.ext = file.ext
			self.padding = file.padding
			self.seq_name = file.get_seq_key(cfg.ignore_padding)
		elif file.frame in self._frames:
			raise IndexError('%s already in sequence as %s' %
							 (file.name, self._frames[file.frame]))
		elif self.padding < file.padding:
			self.inconsistent_padding = True
			self.padding = file.padding
		self._frames[file.frame] = file

	def format(self, format=cfg.format):
		"""
		This formatter will replace any of the formatting directives
		found in the format argument with it's string part. It will try
		to format any character after a % sign, so in order to use a
		literal %, it must be escaped with another % - '%%'.

		 --------------------------------------------------------------------
		|  SAMPLE NAME:   '/path/to/file_name.0101.final.ext'
		 --------------------------------------------------------------------

		  FMT     DESCRIPTION                      EXAMPLE
		 --------------------------------------------------------------------
		| '%%' |  literal '%' sign               |  '%'
		|--------------------------------------------------------------------
		| '%p' |  pathname                       |  '/path/to'
		|--------------------------------------------------------------------
		| '%h' |  head chars of filename         |  'file_name.'
		|--------------------------------------------------------------------
		| '%H' |  all chars preceeding frame #   |  '/path/to/file_name.'
		|--------------------------------------------------------------------
		| '%f' |  number of actual frames        |  '42'
		|--------------------------------------------------------------------
		| '%r' |  implied frame range            |  '[0101-0150]'
		|--------------------------------------------------------------------
		| '%R' |  broken explicit frame range    |  '[101-140, 148, 150]'
		|      |  ignores padding                |
		|--------------------------------------------------------------------
		| '%m' |  total number of missing frames |  '8'
		|--------------------------------------------------------------------
		| '%M' |  broken explicit missing ranges |  '[141-147, 149]'
		|      |  ignores padding                |
		|--------------------------------------------------------------------
		| '%D' |  '#' digits denoting padding    |  '####'
		|--------------------------------------------------------------------
		| '%P' |  '%' style padding              |  '%04d'
		|--------------------------------------------------------------------
		| '%t' |  tail chars after frame, no ext |  '.final'
		|--------------------------------------------------------------------
		| '%T' |  all tail chars after frame     |  '.final.ext'
		|--------------------------------------------------------------------
		| '%e' |  extension without dot          |  'ext'
		 --------------------------------------------------------------------

		:param format: the string directive for the formatter to convert
		:return: the formatted string
		"""

		# Call functions to minimize processes run during formatter execution.
		directive_mapper = {
			'%%': self.__pct,
			'%p': self.__path,
			'%h': self.__namehead,
			'%H': self.__head,
			'%f': self.__num_frames,
			'%r': self.__implied_range,
			'%R': self.__explicit_range,
			'%m': self.__num_missing_frames,
			'%M': self.__explicit_missing_range,
			'%D': self.__digits_pound_signs,
			'%P': self.__digits_padding,
			'%t': self.__tail_without_ext,
			'%T': self.__tail,
			'%e': self.__ext,
		}
		format = [c for c in format]
		new_string = ''

		matched = False
		for char in format:
			if matched:
				new_string += directive_mapper['%' + char]()
				matched = False
				continue
			if char == '%':
				matched = True
				continue
			else:
				new_string += char
		return new_string

	def __pct(self):
		""" Internal formatter method """
		return '%'

	def __path(self):
		""" Internal formatter method """
		return self.path

	def __namehead(self):
		""" Internal formatter method """
		return self.namehead

	def __head(self):
		""" Internal formatter method """
		return self.head

	def __num_frames(self):
		""" Internal formatter method """
		return str(self.frames)

	def __implied_range(self):
		""" Internal formatter method """
		return '[' + str(self.get_frame(self.start).frame_as_str) + \
			   '-' + str(self.get_frame(self.end).frame_as_str) + ']'

	def __explicit_range(self):
		""" Internal formatter method """
		return frame_ranges_to_string(sorted(self._frames))

	def __num_missing_frames(self):
		""" Internal formatter method """
		return str(self.missing_frames)

	def __explicit_missing_range(self):
		""" Internal formatter method """
		return frame_ranges_to_string(self.get_missing_frames())

	def __digits_pound_signs(self):
		""" Internal formatter method """
		return '#' * self.padding

	def __digits_padding(self):
		""" Internal formatter method """
		return '%%0%dd' % self.padding

	def __tail_without_ext(self):
		""" Internal formatter method """
		return '.'.join(self.tail.split('.')[:-1])

	def __tail(self):
		""" Internal formatter method """
		return self.tail

	def __ext(self):
		""" Internal formatter method """
		return self.ext
