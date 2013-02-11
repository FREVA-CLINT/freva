'''
Created on 08.02.2013

@author: estani
'''

class Item(object):
    def __init__(self, value, previous=None):
        self.value = value
        self.next = None
        
        if previous:
            self.previous = previous
            previous.next = self
    def detach(self):
        self.next.previous = None
        self.next = None
    def __repr__(self):
        return self.value.__repr__()

class BufferedGenerator(object):
    def __init__(self, generator, buffersize=4):
        self.size = buffersize
        self._gen = generator
    def __iter__(self):
        previous=None
        end=None
        count = self.size
        for i in self._gen:
            current = Item(i, previous=previous)
            
            if count == 0:
                end = end.next
                end.previous.detach()                
            else:
                if count == self.size:
                    end = current
                count -= 1
            yield current
            previous=current
                
from struct import unpack, pack
from datetime import datetime, timedelta
from inspect import currentframe, getargvalues
import re
import os

_HEADER = '<lli'    
"""Each entry of ttyrec is preceded by a 12byte header::

    time_sv (long int sec, long int usec)
    int length

sec: seconds since epoch
usec: microseconds (since last second :-)
length: length of the following payload in bytes.
"""

_HEADER_SIZE = 3*4
"3 * 4 (12) bytes"

_TIMESTAMP = '%Y-%m-%d %H:%M:%S.%f'
_TIMESTAMP_OFFSET = '%s.%f'
"This is the format of the exported time stamp when converting to/from ascii."

_ASCII_HEAD = re.compile('^\[([0-9:. -]*)\] ([0-9]*)(?: ([a-z,=.A-Z0-9]*))?$')
"For extracting the header info stored in ascii."

class Options(dict):
    @staticmethod
    def from_str(opt_str):
        parsed_dict = {}
        for opt in opt_str.split(','):
            if '=' in opt:
                key, value = opt.split('=')
            else:
                key, value = opt, None
            parsed_dict[key] = value
        return Options(parsed_dict)
    def add(self, str_val):
        self.update(Options.from_str(str_val))
        
    def __str__(self):
        values = []
        for key, value in self.items():
            if value is None:
                values.append(key)
            else:
                values.append('%s=%s' % (key, value))
        return ','.join(values)     

class Stream(object):
    """Handle any string pointing to a path or any other similar object and close
only if required (i.e. if it was opened here)"""
    def __init__(self, path, *opts):
        if isinstance(path, basestring):
            path = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
            self.stream = open(path, *opts)
            self.closeOnExit = True
        else:
            #don't close anything it wasn't opened here.
            self.stream = path
            self.closeOnExit = False
    def __enter__(self):
        return self.stream
    def __exit__(self, exc_type, value, traceback):
        if self.closeOnExit:
            self.stream.close()

class TTYrecEntry(object):
    def __init__(self, duration, payload, options = None):
        self.duration = duration
        self.payload = payload
        if options:
            self.options = options
        else:
            self.options = Options()
    def __str__(self):
        if len(self.payload) > 10:
            payload = repr(self.payload[:11]) + '...'
        else:
            payload = self.payload
        return '[%s] %s %s\n%s\n' % (self.duration, len(self.payload), self.options, payload)

    def __repr__(self):
        return '[%s] %s %s\n%s\n' % (self.duration, len(self.payload), self.options, self.payload)
        
class TTYrecStream(object):
    """This objects encapsulates all handling of ttyrec files and their ascii representation.
It works also as a generator so you can iterate the results as may times as required.
The operations applied are stored and reapplied every time the generator is run.
This means that no access is being done until required, each element is accessed only once
and on demand.
All methods return the object itself to easy concatenation. This is an example::

    from ttyrec.io import TTYrecStream
    
    #load a file and add some intro (file is not being read at this time)
    basic = TTYrecStream.load_ttyrec('/tmp/a_file').add_intro(intro_delay=2)
    
    #print the first five entries without ever accessing all the file
    import itertools
    print list(itertools.islice(basic, 0 , 5))
    
    #continue processing
    basic.mark_input().delay_input(delay_after_input=2.5)
    
    #write the file without every getting all the file to memory
    basic.write_ascii('/tmp/ascii_repr')

There is no buffer strategy in place besides the default system stratgegy for handling the "open" call.
defining this would be very simple. 
"""
    def __init__(self):
        """Prepare the process pipe and the empty generator"""
        self._process_pipe = []
        self._gen = None

    def __store(self):
        """Store the method being called for re-play."""
        frame = currentframe(1)
        arg_spec = getargvalues(frame)
        name = frame.f_code.co_name
        args = {}
        for var_name in arg_spec[0] + list(arg_spec[1:3]):
            if var_name and var_name != 'self':
                args[var_name] = arg_spec.locals[var_name]
        self._process_pipe.append((name, args))
        return self
    
    def __reload(self):
        """Reloads the configuration to setup the generator again."""
        proc_pipe = self._process_pipe
        self._process_pipe = []
        for method, args in proc_pipe:
            getattr(self,method)(**args)

    def __iter__(self):
        """Returns the setup iterator and prepare a new one"""
        it = self._gen
        self.__reload()
        return it
    
    def load_ttyrec(self, tty_file):
        """Reads a ttyrec binary file.

:param tty_file: ttyrecord binary input file.
:returns: This object"""
        def gen():
            with Stream(tty_file, 'rb') as fin:
                last = None
                try:
                    while True:
                        sec, usec, length = unpack(_HEADER, fin.read(_HEADER_SIZE))
                        payload = fin.read(length)
                        
                        #ready
                        tstamp = sec + usec / 1000000.0
                        if last is None:
                            last = tstamp
                        
                        yield TTYrecEntry(tstamp-last, payload)
                        last = tstamp
                except:
                    pass
        self._gen = gen()
        return self.__store()
    
    def load_ascii(self, ascii_file):
        """Reads an ascii file representing a ttyrec binary.

:param ascii_file: ascii input file.
:returns: This object"""
        def gen():
            entry_nr=0
            line_nr=0
            with Stream(ascii_file, 'r') as fin:
                try:
                    while True:
                        line = fin.readline()
                        entry_nr += 1
                        line_nr += 1
                        if not line: break
                        
                        #get strings
                        timing, length, options = _ASCII_HEAD.match(line).groups()
                        #parse values
                        timing = float(timing)
                        length = int(length)
                        if options:
                            options = Options.from_str(options)
                        
                        payload = fin.read(length)
                        line_nr += payload.count('\n')
                            
                        yield TTYrecEntry(timing, payload, options)
                        assert(fin.read(1)=='\n') #There should be a carriage return separating each entry
                        line_nr +=1
                except:
                    print "Error in entry %s (line~%s): %s" % (entry_nr, line_nr, line)
                    raise
        self._gen = gen()
        return self.__store()
    
    def save_ascii(self, ascii_file):
        """Writes result to an ascii file.

:param ascii_file: ascii output file.
    """
        with Stream(ascii_file, 'w') as fout:
            for entry in self._gen:
                #allow some simple time manipulation
                fout.write('[%s] %s %s\n%s\n' % (entry.duration, len(entry.payload), entry.options, entry.payload))
            
        #we have consumed the iterator, set it up again
        self.__reload()
        return self
        
    def save_ttyrec(self, tty_file):
        """Writes result to a ttyrec binary file that can be replayed with ttyplay.
        
:param tty_file: ttyrecord binary output file."""
        runtime = 0.0
        with Stream(tty_file , 'wb') as fout:
            for entry in self._gen:
                length = len(entry.payload)
                runtime += entry.duration
                sec = int(runtime)
                usec = int((runtime-int(runtime)) * 1000000)
                header = pack(_HEADER, sec, usec, length)
                
                fout.write(header)
                fout.write(entry.payload)
                
        #we have consumed the iterator, set it up again
        self.__reload()
        return self
        
    #EFFECTS
    def teletype(self, sec_per_char=0.05):
        from random import Random
        r = Random(0)
        def jitter_func(duration, jitter=None, max_delay=None, cap_to_max=True):
            if max_delay is None: max_delay = 2 * duration
            if duration >= max_delay: return max_delay
            if jitter is None: jitter=0.02
            #value between 0 and max_delay that gets to duration if jitter gets to  0
            if r.random() < 0.5: 
                return duration * (1-(r.random() * jitter))
            else: 
                return duration + (max_delay-duration)  * (r.random() * jitter)
            
            
        def gen(old_generator):
            for entry in old_generator:
                if 'i' in entry.options and len(entry.payload) > 1:
                        char_duration = entry.options['i']
                        if char_duration is None: char_duration = sec_per_char
                        else: char_duration = float(char_duration)
                        jitter = entry.options.get('j', None)
                        if jitter is not None: jitter = float(jitter)
                        
                        first = True
                        #this is input we must extend it in a typewriter similar manner
                        for c in entry.payload:
                            if first:
                                duration = entry.duration
                                first = False
                            else:
                                duration = jitter_func(char_duration, jitter)
                            #should we copy the options? Does it make sense?
                            yield TTYrecEntry(duration, c, entry.options)
                else:         
                    yield entry

        self._gen = gen(self._gen)
        return self.__store()

    def cap_delays(self, max_delay=3):
        """Reduces all delay to the given maximum.
    
:param max_delay: maximal number of seconds to wait between any kind of feedback (i.e. input or output)."""
        def gen(old_generator):
            for entry in old_generator:
                if entry.duration > max_delay:
                    entry.duration = max_delay
                
                yield entry  
        self._gen = gen(self._gen)
        return self.__store()
    
    def change_speed(self, speed=1.0):
        """changes the recorded speed to the given one.
    
:param speed: speed factor (<1 = slower, >1 = faster)."""
        def gen(old_generator):
            for entry in old_generator:
                    entry.duration *= speed
                    yield entry
        self._gen = gen(self._gen)
        return self.__store()
    
    def add_intro(self, intro_delay=1):
        """Clears the screen before starting and remain like that for a while.
    
:param intro_delay: number of seconds (or fraction) to remain with the screen black."""
        def gen(old_generator):
            show_intro = True
            clear_screen = '\x1b[H\x1b[2J'
            
            for entry in old_generator:
                if show_intro:
                    show_intro = False
                    yield TTYrecEntry(intro_delay, clear_screen)
                    
                yield entry
        self._gen = gen(self._gen)
        return self.__store()
    
    def split_lines(self, delay_per_line=0.05):
        """Break lines stored and show them with some delay, line by line.
        
:param delay_per_line: seconds (or fraction) to wait between lines"""
        def gen(old_generator):
            in_input = False
            for entry in old_generator:
                if 'i' in entry.options:
                    in_input = True
                    #don't affect input
                    yield entry
                elif in_input:
                    in_input = False
                    #don't affect first line after input
                    yield entry
                else:                   
                    for line in entry.payload.splitlines(True):
                        yield TTYrecEntry(delay_per_line, line, entry.options)
                
                
        self._gen = gen(self._gen)
        return self.__store()
    
    def delay_input(self, delay_before_input=0, delay_after_input=1):
        """Adds some delay before and/or after the input is done.
        
:param delay_before_input: seconds (or fraction) to wait before input starts.
:param delay_after_input: seconds (or fraction) to wait after input finishes."""
        def gen(old_generator):
            in_input = False
            for entry in old_generator:
                if 'i' in entry.options:
                    if not in_input:
                        entry.duration = delay_before_input
                        in_input = True
                elif in_input:
                    #getting out of input
                    entry.duration = delay_after_input 
                    in_input = False
                yield entry
        self._gen = gen(self._gen)
        return self.__store()
    
    def raw_effect(self, func=None):
        if func is not None:
            def gen(old_generator):
                for entry in old_generator:
                    yield func(entry)
        self._gen = gen(self._gen)
        return self.__store()
    
    def effect(self, generator):
        self._gen = generator(self._gen)
        return self.__store()
    
    def merge_lines(self, threshold=0.01, merge_input=False):
        """Merge lines with less than threshold seconds pause together."""
        def gen(old_generator):
            last_entry = None
            for entry in old_generator:
                if last_entry:
                    if entry.duration < threshold and ('i' not in entry.options or merge_input):
                        #we preserve the options from the first entry
                        last_entry.duration += entry.duration
                        last_entry.payload += entry.payload
                        continue
                    yield last_entry
                last_entry = entry
            #send the last entry
            if last_entry is not None:
                yield last_entry
        self._gen = gen(self._gen)
        return self.__store()
    
    def mark_input(self, prompt_suffix=' $ '):
        """Mark lines following what is defined to be the end of the prompt as input 
(if not already marked as such)"""
        def gen(old_generator):
            next_is_input = False
            for entry in old_generator:
                if next_is_input:
                    next_is_input = False
                    if 'i' not in entry.options: entry.options.add('i')
                elif entry.payload.endswith(prompt_suffix):
                    next_is_input = True
                yield entry
        self._gen = gen(self._gen)
        return self.__store()
        
        
from time import sleep
import curses
import sys
class Player(object):
    CMDS = dict(PAUSE=map(ord, 'p .'),
                QUIT=[ord('q')],
              FASTER=[ord('f'), curses.KEY_NPAGE],
              SLOWER=[ord('s'), curses.KEY_PPAGE],
              NORM_SPEED=map(ord, '01') + [curses.KEY_F5])
    def __init__(self):
        self._stream = None
        
    def load(self, tty_file, teletype=True, delay_lines=True, ascii=False):
        if isinstance(tty_file, TTYrecStream):
            self._stream = tty_file
        else:
            self._stream = TTYrecStream()
            #we might want to get the first characters of the file and infer if it's ascii
            if ascii:
                self._stream.load_ascii(tty_file)
                if teletype: self._stream.teletype()
                if delay_lines: self._stream.split_lines()
            else:
                self._stream.load_ttyrec(tty_file)
        
        
    def play(self, speed=1.0, interactive=True):
        try:
            w = curses.initscr()
            w.nodelay(True)
            w.keypad(True)
            curses.noecho()
            start = datetime.now()
            running_time = 0.0
            running = True
            for entry in self._stream:
                if interactive:
                    try:
                        while True:
                            #we consume all events before proceeding
                            #to avoid processing old signals
                            key = w.getch()
                            if key == curses.ERR:
                                #all events has been consumed
                                break
                            if key in Player.CMDS['QUIT']:
                                running=False
                            elif key in Player.CMDS['PAUSE']:
                                w.nodelay(False)
                                while True:
                                    key = w.getch()
                                    if key in Player.CMDS['PAUSE']:
                                        break
                                w.nodelay(True)
                            elif key in Player.CMDS['FASTER']:
                                if speed < 10:
                                    speed *= 1.5
                            elif key in Player.CMDS['SLOWER']:
                                if speed > 0.01:
                                    speed /= 1.5
                            elif key in Player.CMDS['NORM_SPEED']:
                                speed = 1
                                
                    except:
                        pass
                
                if not running:
                    break
                running_time += entry.duration
                sleep(entry.duration / speed)
                sys.stderr.write(entry.payload)
                sys.stderr.flush() 
            recording_time=timedelta(seconds=running_time)
            play_time=datetime.now() - start
            sys.stderr.write("\n\r*** END ***\r\n<Hit any key to exit>")
            w.nodelay(False)
            w.getch()
        finally:
            curses.endwin()

        print "Recording: %s" % recording_time
        print "Play time: %s" % play_time

        