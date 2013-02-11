"""This effects are thought as examples of what can be used for the raw_effect
They would be used like::

    TTYrecStream().read_ascii('file.ascii').delay_lines(delay_per_line=0.05).raw_effect(
        LinearInputDelay(start_delay=0.1, end_delay=0.01, duration=600).linear_delay)\
        .write_ascii('/tmp/test1.ascii')

"""
class LinearInputDelay(object):
    def __init__(self, start_delay=0.1, end_delay=0.01, duration=600):
        self.start_delay = start_delay
        self.end_delay = end_delay
        self.duration = duration
        
        self.running_time = 0.0
    def linear_delay(self, entry):
        if 'i' in entry.options:
            #just interpolate linearly between the two values
            
            factor = min(self.running_time, self.duration)/self.duration
            entry.options['i']= self.start_delay * (1 - factor) + self.end_delay * factor
        self.running_time += entry.duration
        return entry

def RemoveWindowSize(generator):
    import re
    cr = re.compile(r' \r(:?[^\n]|$)')
    for entry in generator:
        if 'i' in entry.options:
            entry.payload = cr.sub(r'\1', entry.payload)
        yield entry